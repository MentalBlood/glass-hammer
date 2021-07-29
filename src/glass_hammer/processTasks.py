import os
import sys
import time
import json
import argparse
import requests
import subprocess
import importlib.util
from tqdm.auto import tqdm
from types import FunctionType
from multiprocessing.pool import ThreadPool

from common import addresses



def importModuleFromPath(name, path):
	
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)

	return module



def appendSpaces(s, max_length):
	return s + ' ' * (max_length - len(s))


def updateBarsOnVizualizationServer(bars):

	bars_info = {b.desc.strip(): {
		'current': b.n,
		'total': b.total,
		'elapsed': b.format_dict['elapsed'],
		'average_speed': b.n / (b.format_dict['elapsed'] + 0.001),
		'chart_data': b.chart_data
	} for b in bars}
	
	json_to_send = {
		'name': 'template',
		'data': bars_info
	}
	
	requests.post(
		f"{addresses.vizualization_server['address']}/set",
		headers={
			'content-type': 'application/json; charset=utf-8',
			'Access-Control-Allow-Origin': '*'
		},
		json=json_to_send
	)


def getDelta(chart_data, field_name, current):
	last = 0 if len(chart_data) == 0 else chart_data[-1][field_name]
	return current - last


def watch(watch_functions, stop_when_values, delay, additional_variables):
	
	global_variables = {
		**globals(), 
		**additional_variables
	}

	max_function_description_length = max(map(len, watch_functions.keys()))
	bars = [
		tqdm(
			total=int(stop_when_values[name]),
			desc=appendSpaces(name, max_function_description_length + 1),
		)
		for name in watch_functions.keys()
	]
	
	for b in bars:
		b.chart_data = []

	threads_number = len(watch_functions)
	
	while True:

		results = list(
			ThreadPool(threads_number).map(
				lambda f: f(), 
				list(watch_functions.values())
			)
		)

		for i in range(len(results)):
			bars[i].update(results[i] - bars[i].n)
			current_elapsed = bars[i].format_dict['elapsed']
			current_current = bars[i].n
			bars[i].chart_data.append({
				'elapsed': current_elapsed,
				'current': current_current,
				'average_speed': getDelta(bars[i].chart_data, 'current', current_current) / (getDelta(bars[i].chart_data, 'elapsed', current_elapsed) + 0.0001)
			})
		
		updateBarsOnVizualizationServer(bars)
		
		if all(map(lambda b: b.n == b.total, bars)):
			break
		
		time.sleep(delay - time.time() % delay)
	
	for b in bars:
		b.close()


def closeWindows(names):
	
	for n in names:
		if type(n) == dict:
			os.system(f'timeout {n["delay"]} & taskkill /F /FI "WindowTitle eq {n["name"]}" /T > nul')
		elif type(n) == str:
			os.system(f'taskkill /F /FI "WindowTitle eq {n}" /T > nul')


def processTask(task, input_variables):
	
	additional_variables = input_variables

	if 'init_file' in task:
		init_module = importModuleFromPath('init_module', task['init_file'])
		init_result = init_module.init()
		additional_variables = {**additional_variables, **init_module.__dict__, **init_result}

	if 'commands_to_execute' in task:
		commands_to_execute = task['commands_to_execute']
		for c in commands_to_execute:
			print(f'executing command "{c}"')
			if type(c) == str:
				os.system(c)
			elif type(c) == dict:
				command = c['command']
				window_name = c['window_name']
				after_command = "timeout -1" if 'dont close' in c else "exit"
				os.system(f'start "{window_name}" cmd /c "{command} & {after_command}"')

	if 'watch_functions_file' in task:
		watch_functions_module = importModuleFromPath('watch_functions_module', task['watch_functions_file'])
		watch_functions = watch_functions_module.getWatchFunctions(init_result)
		additional_variables = {**additional_variables, **watch_functions_module.__dict__}
		watch(watch_functions, task['stop_when_values'], task['delay'], additional_variables)

	if 'init_file' in task:
		init_module.after(init_result)

	if 'windows_to_close_names' in task:
		closeWindows(task['windows_to_close_names'])


def flattenRecursiveTasks(tasks):
	
	result = []
	
	for t in tasks:
		result.append({k: t[k] for k in t if k != 'subtasks'})
		if 'subtasks' in t:
			result += flattenRecursiveTasks(t['subtasks'])
	
	return result


def processTasks(file_path, additional_variables, command_line_args=sys.argv):
	
	tasks_module = importModuleFromPath('tasks_module', file_path)
	tasks_args_definition = tasks_module.args
	
	tasks_args_parser = argparse.ArgumentParser(description=f'Parser for tasks file {file_path}')
	for names, default_value in tasks_args_definition.items():
		tasks_args_parser.add_argument(
			f'-{names[0]}',
			f'--{names[1]}', 
			type=type(default_value), 
			default=default_value
		)
	tasks_args_namespace, _ = tasks_args_parser.parse_known_args(command_line_args)
	tasks_args = {
		a: getattr(tasks_args_namespace, a)
		for a in dir(tasks_args_namespace)
		if not a.startswith('_')
	}

	input_variables = {
		**tasks_args,
		**additional_variables,
		**globals()
	}
	
	tasks = FunctionType(tasks_module.tasks.__code__, input_variables)()
	flatten_tasks = flattenRecursiveTasks(tasks)
	for t in flatten_tasks:
		processTask(t, input_variables)


import sys
sys.modules[__name__] = processTasks