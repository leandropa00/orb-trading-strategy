import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import traceback
import config
import time
from schwab.auth import client_from_token_file
from schwab.history import HistoryClient
import matplotlib.pyplot as plt

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Símbolos a analizar
simbolos = ["AAPL", "TSLA", "META", "NFLX", "AMZN", "GOOGL", "MSFT", "JPM", "NVDA", "PLTR", "ROKU", "V", "TGT", "SPY", "QQQ", "DIA"]

# Configuraciones de velas a probar
configuraciones_velas = [6, 4, 3]

# Configuraciones de target multiplier a probar
configuraciones_target = [4, 3, 2]

# Configuración base
capital_inicial = 100000
posicion_size = 0.5  # 50% del capital por operación
stop_loss_distance = 0.25  # Distancia del stop loss desde el precio de entrada
hora_cierre_forzado = datetime.strptime("15:55", "%H:%M").time()

# Definir horarios
HORA_APERTURA_MERCADO = datetime.strptime("09:30", "%H:%M").time()
HORA_CIERRE_MERCADO = datetime.strptime("16:00", "%H:%M").time()

# Configuración de fechas
start_date = "2024-02-19"
end_date = "2024-03-19"

def obtener_datos(symbol, start_date=None, end_date=None):
    """Obtiene datos históricos de Schwab"""
    try:
        logger.info(f"Obteniendo datos de Schwab para {symbol}...")
       
        # Crear cliente de Schwab
        client = client_from_token_file(
            token_path=config.TOKEN_PATH,
            api_key=config.API_KEY,
            app_secret=config.APP_SECRET
        )
       
        # Crear cliente de historia
        history_client = HistoryClient(client)
       
        # Convertir fechas a timestamps
        start_ts = int(pd.Timestamp(start_date).timestamp())
        end_ts = int(pd.Timestamp(end_date).timestamp())
       
        logger.info(f"Solicitando datos desde {start_date} hasta {end_date}")
       
        # Obtener datos históricos
        data = history_client.get_history(
            symbol=symbol,
            interval='5',  # 5 minutos
            start=start_ts,
            end=end_ts
        )
       
        if not data:
            logger.warning(f"No se recibieron datos para {symbol}")
            return None
           
        # Convertir a DataFrame
        df = pd.DataFrame(data)
       
        # Convertir timestamp a datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
       
        # Convertir a zona horaria EST/EDT
        df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
       
        # Configurar índice y columnas
        df.set_index('datetime', inplace=True)
        df = df[['open', 'high', 'low', 'close']]
        df.sort_index(ascending=True, inplace=True)
       
        logger.info(f"Datos obtenidos exitosamente para {symbol}: {len(df)} registros")
        return df
       
    except Exception as e:
        logger.error(f"Error obteniendo datos de Schwab para {symbol}: {str(e)}")
        traceback.print_exc()
        return None

def simular_operacion(df, symbol, n_candles, target_multiplier):
    """Simula operaciones de trading basadas en las señales"""
    capital = capital_inicial
    posicion_actual = None
    tx_log = []
   
    # Agrupar datos por fecha
    df['fecha'] = df.index.date
    df['hora'] = df.index.time
   
    # Para cada día de trading
    for fecha, grupo in df.groupby('fecha'):
        # Resetear posición para el nuevo día
        posicion_actual = None
       
        # Ordenar las velas por hora
        grupo = grupo.sort_index()
       
        # Filtrar solo sesión de la mañana (9:30 - 12:00)
        grupo = grupo.between_time('09:30', '12:00')
       
        # Verificar si hay suficientes datos
        if len(grupo) < n_candles + 1:
            continue
           
        # Obtener las primeras n_candles velas
        primeras_velas = grupo.iloc[:n_candles]
       
        # Calcular el rango
        rango_alto = primeras_velas['high'].max()
        rango_bajo = primeras_velas['low'].min()
       
        # Obtener la última vela del rango
        ultima_vela_rango = primeras_velas.iloc[-1]
        rango_ultima_vela = ultima_vela_rango['high'] - ultima_vela_rango['low']
       
        # Analizar velas posteriores
        for i in range(n_candles, len(grupo)):
            vela = grupo.iloc[i]
           
            # Verificar señales
            if posicion_actual is None:
                if vela['high'] > rango_alto:  # Señal de compra
                    entrada = vela['close']
                    stop_loss = entrada * (1 - stop_loss_distance)
                    target = entrada * (1 + (stop_loss_distance * target_multiplier))
                   
                    posicion_actual = {
                        'entrada_fecha': vela.name,
                        'precio_entrada': entrada,
                        'tipo': 'LONG',
                        'stop_loss': stop_loss,
                        'target': target
                    }
                   
                elif vela['low'] < rango_bajo:  # Señal de venta
                    entrada = vela['close']
                    stop_loss = entrada * (1 + stop_loss_distance)
                    target = entrada * (1 - (stop_loss_distance * target_multiplier))
                   
                    posicion_actual = {
                        'entrada_fecha': vela.name,
                        'precio_entrada': entrada,
                        'tipo': 'SHORT',
                        'stop_loss': stop_loss,
                        'target': target
                    }
           
            # Si hay posición abierta, verificar salida
            elif posicion_actual is not None:
                if posicion_actual['tipo'] == 'LONG':
                    if vela['low'] <= posicion_actual['stop_loss']:  # Stop loss
                        salida = posicion_actual['stop_loss']
                        resultado = (salida - posicion_actual['precio_entrada']) / posicion_actual['precio_entrada']
                       
                        tx_log.append({
                            'fecha_entrada': posicion_actual['entrada_fecha'],
                            'fecha_salida': vela.name,
                            'precio_entrada': posicion_actual['precio_entrada'],
                            'precio_salida': salida,
                            'tipo': posicion_actual['tipo'],
                            'resultado': resultado,
                            'capital': capital * (1 + resultado * posicion_size)
                        })
                       
                        capital = capital * (1 + resultado * posicion_size)
                        posicion_actual = None
                       
                    elif vela['high'] >= posicion_actual['target']:  # Take profit
                        salida = posicion_actual['target']
                        resultado = (salida - posicion_actual['precio_entrada']) / posicion_actual['precio_entrada']
                       
                        tx_log.append({
                            'fecha_entrada': posicion_actual['entrada_fecha'],
                            'fecha_salida': vela.name,
                            'precio_entrada': posicion_actual['precio_entrada'],
                            'precio_salida': salida,
                            'tipo': posicion_actual['tipo'],
                            'resultado': resultado,
                            'capital': capital * (1 + resultado * posicion_size)
                        })
                       
                        capital = capital * (1 + resultado * posicion_size)
                        posicion_actual = None
                       
                elif posicion_actual['tipo'] == 'SHORT':
                    if vela['high'] >= posicion_actual['stop_loss']:  # Stop loss
                        salida = posicion_actual['stop_loss']
                        resultado = (posicion_actual['precio_entrada'] - salida) / posicion_actual['precio_entrada']
                       
                        tx_log.append({
                            'fecha_entrada': posicion_actual['entrada_fecha'],
                            'fecha_salida': vela.name,
                            'precio_entrada': posicion_actual['precio_entrada'],
                            'precio_salida': salida,
                            'tipo': posicion_actual['tipo'],
                            'resultado': resultado,
                            'capital': capital * (1 + resultado * posicion_size)
                        })
                       
                        capital = capital * (1 + resultado * posicion_size)
                        posicion_actual = None
                       
                    elif vela['low'] <= posicion_actual['target']:  # Take profit
                        salida = posicion_actual['target']
                        resultado = (posicion_actual['precio_entrada'] - salida) / posicion_actual['precio_entrada']
                       
                        tx_log.append({
                            'fecha_entrada': posicion_actual['entrada_fecha'],
                            'fecha_salida': vela.name,
                            'precio_entrada': posicion_actual['precio_entrada'],
                            'precio_salida': salida,
                            'tipo': posicion_actual['tipo'],
                            'resultado': resultado,
                            'capital': capital * (1 + resultado * posicion_size)
                        })
                       
                        capital = capital * (1 + resultado * posicion_size)
                        posicion_actual = None
   
    return pd.DataFrame(tx_log) if tx_log else pd.DataFrame()

def calcular_estadisticas(df_tx, symbol, n_candles, target_multiplier):
    """Calcula estadísticas detalladas del backtest"""
    if len(df_tx) == 0:
        return None
   
    # Estadísticas básicas
    num_operaciones = len(df_tx)
    num_ganadoras = len(df_tx[df_tx['resultado'] > 0])
    num_perdedoras = len(df_tx[df_tx['resultado'] <= 0])
   
    # Rentabilidad
    winrate = (num_ganadoras / num_operaciones) * 100
    avg_win = df_tx[df_tx['resultado'] > 0]['resultado'].mean() * 100
    avg_loss = df_tx[df_tx['resultado'] <= 0]['resultado'].mean() * 100
    profit_factor = abs(avg_win * num_ganadoras / (avg_loss * num_perdedoras)) if num_perdedoras > 0 else float('inf')
   
    # Retorno y drawdown
    retorno_total = ((df_tx['capital'].iloc[-1] - capital_inicial) / capital_inicial) * 100
    df_tx['drawdown'] = (df_tx['capital'].cummax() - df_tx['capital']) / df_tx['capital'].cummax() * 100
    max_drawdown = df_tx['drawdown'].max()
   
    # Calcular retorno anualizado
    dias_trading = (df_tx['fecha_salida'].max() - df_tx['fecha_entrada'].min()).days
    retorno_anual = ((1 + retorno_total/100) ** (365/dias_trading) - 1) * 100 if dias_trading > 0 else 0
   
    # Ratio Sharpe simplificado (usando retornos diarios)
    retornos_diarios = df_tx.groupby(df_tx['fecha_entrada'].dt.date)['resultado'].sum()
    sharpe_ratio = np.sqrt(252) * retornos_diarios.mean() / retornos_diarios.std() if len(retornos_diarios) > 1 else 0
   
    # Calcular rachas
    racha_actual = 0
    max_racha_ganadora = 0
    max_racha_perdedora = 0
   
    df_tx_ordenado = df_tx.sort_values('fecha_entrada')
    for _, operacion in df_tx_ordenado.iterrows():
        if operacion['resultado'] > 0:
            if racha_actual > 0:
                racha_actual += 1
            else:
                racha_actual = 1
            max_racha_ganadora = max(max_racha_ganadora, racha_actual)
        else:
            if racha_actual < 0:
                racha_actual -= 1
            else:
                racha_actual = -1
            max_racha_perdedora = min(max_racha_perdedora, racha_actual)
   
    return {
        'Symbol': symbol,
        'Candles': n_candles,
        'Target': target_multiplier,
        'Trades': num_operaciones,
        'Win Rate': round(winrate, 2),
        'Avg Win': round(avg_win, 2),
        'Avg Loss': round(avg_loss, 2),
        'Profit Factor': round(profit_factor, 2),
        'Return': round(retorno_total, 2),
        'Annual Return': round(retorno_anual, 2),
        'Max DD': round(max_drawdown, 2),
        'Sharpe': round(sharpe_ratio, 2),
        'Win Streak': max_racha_ganadora,
        'Loss Streak': abs(max_racha_perdedora),
        'Rating': calcular_rating(profit_factor, max_drawdown, retorno_anual, num_operaciones)
    }

def calcular_rating(profit_factor, max_drawdown, retorno_anual, num_operaciones):
    """Calcula una calificación basada en los criterios principales"""
    if num_operaciones < 20:
        return "Insufficient Data"
   
    if profit_factor >= 2.0 and max_drawdown <= 20 and retorno_anual >= 50:
        return "Excellent"
    elif profit_factor >= 1.5 and max_drawdown <= 30 and retorno_anual >= 30:
        return "Good"
    elif profit_factor > 1.0 and retorno_anual > 0:
        return "Average"
    else:
        return "Poor"

def guardar_resultados_excel(resultados, nombre_archivo='ORB_resultados.xlsx'):
    """Guarda resultados y genera gráficos"""
    try:
        # Convertir resultados a DataFrame
        df_resultados = pd.DataFrame(resultados)
       
        # Ordenar por Profit Factor
        df_resultados = df_resultados.sort_values('Profit Factor', ascending=False)
       
        # Guardar en Excel
        with pd.ExcelWriter(nombre_archivo) as writer:
            df_resultados.to_excel(writer, sheet_name='Resultados', index=False)
       
        print(f"\nResultados guardados en {nombre_archivo}")
       
        # Mostrar mejores configuraciones
        print("\nMejores configuraciones por Profit Factor:")
        print(df_resultados.head())
       
    except Exception as e:
        print(f"Error guardando resultados: {str(e)}")
        traceback.print_exc()

def main():
    """Función principal del script"""
    try:
        print("\nIniciando backtesting...")
        print(f"Período: {start_date} a {end_date}")
        print(f"Símbolos: {', '.join(simbolos)}")
        print(f"Configuraciones de velas: {configuraciones_velas}")
        print(f"Multiplicadores de target: {configuraciones_target}")
        print("=" * 50)
       
        resultados = []
        total_combinaciones = len(simbolos) * len(configuraciones_velas) * len(configuraciones_target)
        combinacion_actual = 0
       
        for symbol in simbolos:
            # Obtener datos históricos
            df = obtener_datos(symbol, start_date=start_date, end_date=end_date)
            if df is None:
                continue
           
            # Probar cada combinación de parámetros
            for n_candles in configuraciones_velas:
                for target in configuraciones_target:
                    combinacion_actual += 1
                    print(f"\n[{combinacion_actual}/{total_combinaciones}] Procesando {symbol} - {n_candles} velas - {target}x target")
                   
                    # Simular operaciones
                    df_tx = simular_operacion(df, symbol, n_candles, target)
                   
                    # Calcular estadísticas
                    if len(df_tx) > 0:
                        stats = calcular_estadisticas(df_tx, symbol, n_candles, target)
                        if stats:
                            resultados.append(stats)
                            print(f"Resultados: {stats['Trades']} trades, {stats['Win Rate']}% win rate")
                    else:
                        print("No se encontraron operaciones para esta configuración")
       
        # Guardar resultados
        if resultados:
            guardar_resultados_excel(resultados)
        else:
            print("\nNo se encontraron resultados para guardar")
           
    except Exception as e:
        print(f"Error en el proceso de backtesting: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
