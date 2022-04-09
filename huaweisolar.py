import logging
import time
import huawei_solar
import paho.mqtt.client
import os
import json

FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.INFO)

inverter_ip = os.getenv('INVERTER_IP', '192.168.1.1')
mqtt_host = os.getenv('MQTT_HOST', '192.168.1.1')

inverter = huawei_solar.HuaweiSolar(inverter_ip, port=int(
    os.getenv('INVERTER_PORT', "502")), slave=1)
inverter._slave = 1
inverter.wait = 1

# vars = ['state_1','state_2', 'state_3', 'alarm_1', 'alarm_2', 'alarm_3', 'pv_01_voltage', 'pv_01_current', 'pv_02_voltage','pv_02_current', 'input_power', 'grid_voltage',
#'grid_current', 'day_active_power_peak', 'active_power', 'reactive_power',
#'grid_frequency', 'efficiency', 'internal_temperature', 'insulation_resistance', 'device_status', 'fault_code', 'startup_time', 'shutdown_time', 'accumulated_yield_energy',
#'daily_yield_energy', 'grid_A_voltage', 'active_grid_A_current', 'power_meter_active_power',
# 'grid_exported_energy', 'grid_accumulated_energy']

# vars = ['alarm_1', 'pv_01_voltage', 'pv_01_current', 'pv_02_voltage','pv_02_current', 'input_power', 'grid_voltage',
#'grid_current', 'day_active_power_peak', 'active_power', 'reactive_power',
#'grid_frequency', 'efficiency', 'internal_temperature', 'insulation_resistance', 'device_status', 'fault_code', 'startup_time', 'shutdown_time', 'accumulated_yield_energy',
#'daily_yield_energy', 'grid_A_voltage', 'active_grid_A_current', 'power_meter_active_power',
# 'grid_exported_energy', 'grid_accumulated_energy']

vars_immediate_default = ['pv_01_voltage', 'pv_01_current', 'pv_02_voltage', 'pv_02_current', 'input_power', 'grid_voltage',
                          'grid_current', 'active_power', 'grid_A_voltage', 'active_grid_A_current', 'power_meter_active_power', 'storage_unit_1_total_charge']
vars_cumulative_default = ['day_active_power_peak', 'efficiency', 'internal_temperature', 'insulation_resistance', 'device_status', 'fault_code',
                           'accumulated_yield_energy', 'daily_yield_energy', 'grid_exported_energy', 'grid_accumulated_energy']


def try_modBus_variable(variable):
    try:
        result = inverter.get(variable)
        return {'value': result.value, 'unit': result.unit}
    except:
        log.warning(f"❌ Failed to get {variable}!")
        return {'value': -1, 'unit': "?"}


def modbusAccess():

    vars_immediate = ','.split(
        os.getenv('IMMEDIATE_VARS', ','.join(vars_immediate_default)))
    vars_cumulative = ','.split(
        os.getenv('CUMULATIVE_VARS', ','.join(vars_cumulative_default)))

    cont = 0
    while True:
        immediate_results = {var: try_modBus_variable(
            var) for var in vars_immediate}
        clientMQTT.publish(topic="huawei/node/immediate",
                           payload=json.dumps(immediate_results), qos=1, retain=False)
        log.info('🚀 Publishing immediate results...')

        if(cont > 5):
            results = {var: try_modBus_variable(
                var) for var in vars_cumulative}
            clientMQTT.publish(topic="huawei/node/cumulative",
                               payload=json.dumps(results), qos=1, retain=False)
            log.info('🚀 Publishing cumulative results...')

            cont = 0

        cont += 1
        time.sleep(1)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True  # set flag
        log.info("MQTT OK!")
    else:
        log.info("MQTT FAILURE. ERROR CODE: %s", rc)


paho.mqtt.client.Client.connected_flag = False  # create flag in class
broker_port = int(os.getenv("MQTT_PORT", "1883"))

clientMQTT = paho.mqtt.client.Client()
clientMQTT.on_connect = on_connect  # bind call back function
clientMQTT.loop_start()
log.info("Connecting to MQTT broker: %s ", mqtt_host)
clientMQTT.username_pw_set(username=os.getenv('MQTT_USER', 'user'),
                           password=os.getenv('MQTT_PASS', 'password'))
clientMQTT.connect(mqtt_host, broker_port)  # connect to broker
while not clientMQTT.connected_flag:  # wait in loop
    log.info("...")
time.sleep(1)
log.info("START MODBUS...")

try:
    modbusAccess()
except:
    clientMQTT.loop_stop()
