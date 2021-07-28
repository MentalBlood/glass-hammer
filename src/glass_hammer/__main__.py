import argparse

from glass_hammer import processTasks



parser = argparse.ArgumentParser(description='Tool for transparent testing of non-trivial systems')
parser.add_argument('-v', '--variables', metavar='VAR_FILE', type=str,
					help='input variables file')
parser.add_argument('-t', '--tasks', metavar='TASKS_FILE', type=str,
					help='tasks file path')
args, _ = parser.parse_known_args()


additional_variables = None
try:
	input_variables_module = importModuleFromPath('input_variables_module', args.file)
	module_name = input_variables_module.__name__.split('.')[-1]
	additional_variables = {
		module_name: {
			key: getattr(input_variables_module, key)
			for key in dir(input_variables_module) if not key.startswith('_')
		}
	}
except:
	additional_variables = {}


processTasks(args.tasks, additional_variables)