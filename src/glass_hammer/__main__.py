import os
import argparse

from glass_hammer import processTasks
from glass_hammer.common import importModuleFromPath



parser = argparse.ArgumentParser(description='Tool for transparent testing of non-trivial systems')
parser.add_argument('-v', '--variables', metavar='VAR_FILE', type=str,
					help='input variables file')
parser.add_argument('-t', '--tasks', metavar='TASKS_FILE', type=str,
					help='tasks file path')
parser.add_argument('-s', '--server', metavar='TASKS_FILE', type=str,
					help='vizualization server address', default=None)
args, _ = parser.parse_known_args()


additional_variables = None
try:
	module_name = os.path.basename(args.variables).split('.')[0]
	input_variables_module = importModuleFromPath(module_name, args.variables)
	additional_variables = {
		module_name: input_variables_module
	}
except Exception as e:
	print(e)
	additional_variables = {}
print('additional_variables', additional_variables)


processTasks(args.tasks, additional_variables, args.server)