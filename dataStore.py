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

def toDict(dailyHours, projects, timeRecord):
	readerMap = {}
	maxVer = 0
	for subclass in BaseVersion.__subclasses__():
		readerMap[subclass.version()] = subclass
		maxVer = max(subclass.version(), maxVer)
	return readerMap[maxVer].toDict(dailyHours, projects, timeRecord)


class BaseVersion(ABC):
	@classmethod
	@abstractmethod
	def fromDict(self, serialData):
		pass

	@classmethod
	@abstractmethod
	def toDict(self, dailyHours, projects, timeRecord):
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
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = int(chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == 0:
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[chargeNumber]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != 0:
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		return (dailyHours, projects, timeRecord, prevTime)

	@classmethod
	def toDict(self, dailyHours, projects, timeRecord):
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
		data.update(serialData)

		dailyHours = float(data['dailyHours'])
		projects = []
		projectMap = {}
		for chargeNumberStr, projectAttr in sorted(data['projects'].items()):
			chargeNumber = int(chargeNumberStr)
			project = Project(projectAttr['name'], chargeNumber, projectAttr['billable'])
			projects.append(project)
			if chargeNumber == 0:
				arriveProject = project
			projectMap[chargeNumber] = project
		
		timeRecord = {}
		for dateStr, records in sorted(data['records'].items()):
			date = dt.datetime.strptime(dateStr, '%Y-%m-%d').date()
			timeRecord[date] = {}
			for time, chargeNumber in sorted(records.items()):
				project = projectMap[chargeNumber]
				dtTime = dt.datetime.fromtimestamp(float(time))
				timeRecord[date][dtTime] = project
				if chargeNumber != 0:
					project.addHours(dtTime - prevTime, date)
				prevTime = dtTime
				prevTime = max(prevTime, prevTime)
		return (dailyHours, projects, timeRecord, prevTime)

	@classmethod
	def toDict(self, dailyHours, projects, timeRecord):
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