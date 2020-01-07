from abc import ABC, abstractmethod
from chargeNumberTracker import Project
import datetime as dt

def fromDict(serialData):
	readerMap = {}
	for subclass in BaseVersion.__subclasses__():
		readerMap[subclass.version()] = subclass
	if 'version' in serialData:
		ver = float(serialData['version'])
		if ver in readerMap:
			return readerMap[ver].fromDict(serialData)
	else:
		return v0_0.fromDict(serialData)

def toDict(**kwargs):
	readerMap = {}
	maxVer = 0
	for subclass in BaseVersion.__subclasses__():
		readerMap[subclass.version()] = subclass
		maxVer = max(subclass.version(), maxVer)
	return readerMap[maxVer].toDict(**kwargs)


outDictKeys = ['dailyHours', 
				'projects', 
				'timeRecord', 
				'prevTime', 
				'arriveProject', 
				'recordHoursPath']

inDictKeys = ['dailyHours', 
				'projects', 
				'timeRecord', 
				'recordHoursPath']

class BaseVersion(ABC):
	@classmethod
	@abstractmethod
	def fromDict(self, serialData):
		pass

	@classmethod
	@abstractmethod
	def toDict(self, **kwargs):
		pass

	@classmethod
	@abstractmethod
	def version(self):
		pass

class v0_0(BaseVersion):
	@classmethod
	def fromDict(self, serialData):
		assert(isinstance(serialData, dict))
		data = {}
		data['dailyHours'] = 8.0
		data['projects'] = {}
		data['projects']['0'] = {'billable': False, 'name': 'Arrive'}
		data['projects']['1'] = {'billable': False, 'name': 'Break'}
		data['records'] = {}
		data['version'] = 0
		data['recordHoursPath'] = ''
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = (chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == 0:
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		prevTime = dt.datetime.fromtimestamp(0)
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[str(chargeNumber)]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != 0:
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		return {"dailyHours":dailyHours, 
				"projects":projects, 
				"timeRecord":timeRecord, 
				"prevTime":prevTime, 
				"arriveProject":arriveProject,
				'recordHoursPath':data['recordHoursPath']}

	@classmethod
	def toDict(self, **kwargs):
		raise NotImplementedError()

	@classmethod
	def version(self):
		return 0

class v1_0(BaseVersion):
	@classmethod
	def fromDict(self, serialData):
		assert(isinstance(serialData, dict))
		assert('version' in serialData)
		assert(float(serialData['version']) == 1.0)
		assert('records' in serialData)
		assert('projects' in serialData)
		assert('dailyHours' in serialData)
		data = {}
		data['dailyHours'] = 8.0
		data['projects'] = {}
		data['projects']['0'] = {'billable': False, 'name': 'Arrive'}
		data['projects']['1'] = {'billable': False, 'name': 'Break'}
		data['records'] = {}
		data['version'] = 0
		data['recordHoursPath'] = ''
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = (chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == 0:
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		prevTime = dt.datetime.fromtimestamp(0)
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[str(chargeNumber)]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != 0:
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		return {"dailyHours":dailyHours, 
				"projects":projects, 
				"timeRecord":timeRecord, 
				"prevTime":prevTime, 
				"arriveProject":arriveProject,
				'recordHoursPath':data['recordHoursPath']}

	@classmethod
	def toDict(self, **kwargs):
		dailyHours = kwargs['dailyHours']
		projects = kwargs['projects']
		timeRecord = kwargs['timeRecord']
		data = {}
		data['projects'] = {}
		for project in projects:
			data['projects'][project.chargeNumber] = {'name': project.name, 
				'billable': project.isBillable}

		data['records'] = {}
		for date, records in timeRecord.items():
			data['records'][date.isoformat()] = {}
			for time, project in records.items():
				data['records'][date.isoformat()][dt.datetime.timestamp(time)] = project.chargeNumber
		data['dailyHours'] = dailyHours
		data['version'] = 1.0
		return data

	@classmethod
	def version(self):
		return 1.0

class v1_1(BaseVersion):
	@classmethod
	def fromDict(self, serialData):
		assert(isinstance(serialData, dict))
		assert('version' in serialData)
		assert(float(serialData['version']) == 1.1)
		assert('records' in serialData)
		assert('projects' in serialData)
		assert('dailyHours' in serialData)
		data = {}
		data['dailyHours'] = 8.0
		data['projects'] = {}
		data['projects']['0'] = {'billable': False, 'name': 'Arrive'}
		data['projects']['1'] = {'billable': False, 'name': 'Break'}
		data['records'] = {}
		data['version'] = 0
		data['recordHoursPath'] = ''
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = (chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == "0":
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		prevTime = dt.datetime.fromtimestamp(0)
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[str(chargeNumber)]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != "0":
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		recordHoursPath = data['recordHoursPath']
		return {'dailyHours':dailyHours, 
				'projects':projects, 
				'timeRecord':timeRecord, 
				'prevTime':prevTime, 
				'arriveProject':arriveProject,
				'recordHoursPath':recordHoursPath}

	@classmethod
	def toDict(self, **kwargs):
		dailyHours = kwargs['dailyHours']
		projects = kwargs['projects']
		timeRecord = kwargs['timeRecord']
		recordHoursPath = kwargs['recordHoursPath']
		data = {}
		data['projects'] = {}
		for project in projects:
			data['projects'][project.chargeNumber] = {'name': project.name, 
				'billable': project.isBillable}

		data['records'] = {}
		for date, records in timeRecord.items():
			data['records'][date.isoformat()] = {}
			for time, project in records.items():
				data['records'][date.isoformat()][dt.datetime.timestamp(time)] = project.chargeNumber
		data['dailyHours'] = dailyHours
		data['recordHoursPath'] = recordHoursPath
		data['version'] = 1.1
		return data

	@classmethod
	def version(self):
		return 1.1

class v1_2(BaseVersion):
	@classmethod
	def fromDict(self, serialData):
		assert(isinstance(serialData, dict))
		assert('version' in serialData)
		assert(float(serialData['version']) == 1.2)
		assert('records' in serialData)
		assert('projects' in serialData)
		assert('dailyHours' in serialData)
		data = {}
		data['dailyHours'] = 8.0
		data['projects'] = {}
		data['projects']['0'] = {'billable': False, 'name': 'Arrive'}
		data['projects']['1'] = {'billable': False, 'name': 'Break'}
		data['records'] = {}
		data['version'] = 0
		data['recordHoursPath'] = ''
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = (chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == "0":
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		prevTime = dt.datetime.fromtimestamp(0)
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[str(chargeNumber)]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != "0":
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		recordHoursPath = data['recordHoursPath']
		return {'dailyHours':dailyHours, 
				'projects':projects, 
				'timeRecord':timeRecord, 
				'prevTime':prevTime, 
				'arriveProject':arriveProject,
				'recordHoursPath':recordHoursPath}

	@classmethod
	def toDict(self, **kwargs):
		dailyHours = kwargs['dailyHours']
		projects = kwargs['projects']
		timeRecord = kwargs['timeRecord']
		recordHoursPath = kwargs['recordHoursPath']
		data = {}
		data['projects'] = {}
		for project in projects:
			data['projects'][project.chargeNumber] = {'name': project.name, 
				'billable': project.isBillable}

		data['records'] = {}
		for date, records in timeRecord.items():
			data['records'][date.isoformat()] = {}
			for time, project in records.items():
				data['records'][date.isoformat()][dt.datetime.timestamp(time)] = project.chargeNumber
		data['dailyHours'] = dailyHours
		data['recordHoursPath'] = recordHoursPath
		data['version'] = 1.2
		return data

	@classmethod
	def version(self):
		return 1.2