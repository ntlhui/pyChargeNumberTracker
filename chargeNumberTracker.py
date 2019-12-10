#!/usr/bin/env python3

import tkinter as tk
import numpy as np
import datetime as dt
import json
import platform
import os
import contextlib
import tkcalendar as tkc
import operator
import dataStore

test = True

class Project():
	def __init__(self, name, chargeNumber, isBillable):
		self.name = name
		self.chargeNumber = chargeNumber
		self.hours = {}
		self.isBillable = isBillable

	def addHours(self, hours, date):
		assert(isinstance(hours, float) or isinstance(hours, dt.timedelta))
		if date not in self.hours:
			self.hours[date] = 0
		if isinstance(hours, float):
			self.hours[date] += hours
		elif isinstance(hours, dt.timedelta):
			self.hours[date] += hours.total_seconds() / 60.0 / 60.0

	def getBillableHours(self, date):
		if not self.isBillable:
			return 0
		if date in self.hours:
			return np.round(self.hours[date] * 4) / 4
		else:
			return 0

	def __str__(self):
		return "{%s(%s): %s}" % (self.name, self.chargeNumber, self.hours)

class HourTracker():
	def __init__(self, path):
		self.path = os.path.join(path, 'data.json')
		self.start = None
		self.prevTime = dt.datetime.fromtimestamp(0)
		self.arriveProject = None
		self.addProjectCallback = []
		self.addHoursCallback = []
		self.dailyHours = 0

	def __enter__(self):
		if os.path.isfile(self.path):
			with open(self.path, 'r') as file:
				data = json.load(file)
		else:
			data = {}
		self.dailyHours, self.projects, self.timeRecord, self.prevTime = dataStore.fromDict(data)

	def __exit__(self, exc_type, exc_value, tbk):
		data = dataStore.toDict(self.dailyHours, self.projects, self.timeRecord)
		with open(self.path, 'w') as file:
			json.dump(data, file, indent=4, sort_keys=True)

	def registerAddProjectCallback(self, func):
		self.addProjectCallback.append(func)

	def registerAddHoursCallback(self, func):
		self.addHoursCallback.append(func)

	def getProjectNames(self):
		return {project.name:project for project in self.projects if project.chargeNumber > 0}

	def addProject(self, project):
		self.projects.append(project)
		for func in self.addProjectCallback:
			func(project)

	def __today(self):
		return self.timeRecord[dt.datetime.today().date()]

	def recordArrive(self):
		self.start = dt.datetime.now()
		self.prevTime = self.start
		self.timeRecord[dt.datetime.today().date()] = {}
		self.__today()[self.start] = self.arriveProject
		for func in self.addHoursCallback:
			func(self.arriveProject)

	def recordHours(self, project):
		time = dt.datetime.now()
		self.__today()[time] = project
		project.addHours(time - self.prevTime, time.date())
		self.prevTime = time
		for func in self.addHoursCallback:
			func(project)

	def getTodayTotalHours(self):
		date = dt.datetime.today().date()
		totalHours = 0
		projectHours = self.getHours(date)
		for chargeNumber, hours in projectHours.items():
			totalHours += hours
		return totalHours

	def getTodayRemainingHours(self):
		return self.dailyHours - self.getTodayTotalHours()

	def getEarliestReleaseTime(self):
		return self.prevTime + dt.timedelta(hours=self.getTodayRemainingHours())

	def getHours(self, date):
		retval = {}
		for project in self.projects:
			retval[project.chargeNumber] = project.getBillableHours(date)
		return retval

class HourTrackerViewer(tk.Frame):
	def __init__(self, master, hourTracker):
		self.hourTracker = hourTracker
		super().__init__(master)
		self.timeRecord = hourTracker.timeRecord

		self.innerFrame = None
		self.nameMap = None
		self.__createWidget()
		self.hourTracker.registerAddProjectCallback(self.updateProject)


	def __createWidget(self):
		if self.innerFrame is not None:
			self.innerFrame.destroy()
		self.innerFrame = tk.Frame(self)
		self.dateSelector = tk.StringVar()
		dateEntry = tkc.DateEntry(self.innerFrame, textvariable=self.dateSelector, maxdate=dt.datetime.today())
		dateEntry.grid(row=0, column=0, columnspan=2)
		dateEntry.bind('<<DateEntrySelected>>', self.setDate)

		self.recordFrame = None
		self.setDate()

		self.projectSelector = tk.StringVar()
		self.nameMap = self.hourTracker.getProjectNames()
		self.projectNames = [project.name for project in sorted(self.nameMap.values(), key=operator.attrgetter('chargeNumber'))]
		if len(self.nameMap) > 0:
			self.projectSelector.set(self.projectNames[0])

		tk.OptionMenu(self.innerFrame, self.projectSelector, *tuple(self.projectNames)).grid(row=2, column=0)
		tk.Button(self.innerFrame, text='Record', command=self.recordActivity).grid(row=2, column=1)

		self.innerFrame.grid(row=0, column=0)

	def updateProject(self, project):
		self.__createWidget()

	def update(self):
		self.__createWidget()

	def recordActivity(self):
		projectName = self.projectSelector.get()
		project = self.nameMap[projectName]
		self.hourTracker.recordHours(project)
		self.projectSelector.set(self.projectNames[0])
		self.innerFrame.destroy()
		self.innerFrame = tk.Frame(self)
		self.__createWidget()

	def setDate(self, *args):
		if self.recordFrame is not None:
			self.recordFrame.destroy()
		self.recordFrame = tk.Frame(self.innerFrame)
		date = dt.datetime.strptime(self.dateSelector.get(), '%m/%d/%y').date()
		if date in self.hourTracker.timeRecord:
			row = 0
			for record in sorted(self.hourTracker.timeRecord[date].items()):
				tk.Label(self.recordFrame, text=record[0].strftime('%H:%M')).grid(row=row, column=0)
				tk.Label(self.recordFrame, text=record[1].name).grid(row=row, column=1)
				row += 1
		self.recordFrame.grid(row=1, column=0, columnspan=2)

class ProjectList(tk.Frame):
	def __init__(self, master, hourTracker):
		super().__init__(master)
		self.hourTracker = hourTracker
		self.hourTracker.registerAddHoursCallback(self.updateHours)

		self.innerFrame = None
		self.createWidget()

	def updateHours(self, project):
		self.createWidget()

	def createWidget(self):
		if self.innerFrame is not None:
			self.innerFrame.destroy()
		self.innerFrame = tk.Frame(self)

		row = 0
		today = dt.datetime.today().date()
		for project in sorted(self.hourTracker.projects, key=operator.attrgetter('chargeNumber')):
			if project.chargeNumber > 0:
				tk.Label(self.innerFrame, text=project.name, anchor=tk.NW).grid(row=row, column=0)
				tk.Label(self.innerFrame, text='%s' % (project.chargeNumber), anchor=tk.NW).grid(row=row, column=1)

				billableHours = project.getBillableHours(today)
				if billableHours > 0:
					tk.Label(self.innerFrame, text='%.2f hrs' % (billableHours), anchor=tk.NW).grid(row=row, column=2)
				else:
					tk.Label(self.innerFrame, text="").grid(row=row, column=2)
				row += 1

		self.projectEntry = tk.StringVar()
		self.chargeNumberEntry = tk.StringVar()
		tk.Entry(self.innerFrame, textvariable=self.projectEntry).grid(row=row, column=0)
		tk.Entry(self.innerFrame, textvariable=self.chargeNumberEntry).grid(row=row, column=1)
		tk.Button(self.innerFrame, text='Add Project', command=self.addProject).grid(row=row, column=2)

		tk.Label(self.innerFrame, text="Total Hours: %.2f" % (self.hourTracker.getTodayTotalHours()), anchor=tk.NW).grid(row=0, column=3)
		tk.Label(self.innerFrame, text="Earliest Off Time: %s" % (self.hourTracker.getEarliestReleaseTime().time().strftime('%H:%M')), anchor=tk.NW).grid(row=1, column=3)

		self.innerFrame.grid(row=0, column=0)

	def addProject(self):
		self.hourTracker.addProject(Project(self.projectEntry.get(), int(self.chargeNumberEntry.get())))
		self.projectEntry.set("")
		self.chargeNumberEntry.set('')
		self.createWidget()		

class ChargeNumberTrackerApp:
	def __init__(self):
		self.master = tk.Tk()
		self.master.protocol("WM_DELETE_WINDOW", self.destroy)

		self.master.title('Charge Number Hour Tracker')

		def createMenu():
			menubar = tk.Menu(self.master)
			filemenu = tk.Menu(menubar, tearoff=0)
			filemenu.add_command(label='Arrive', command=self.arrive)
			filemenu.add_command(label='Get Hours', command=self.getHours)
			filemenu.add_command(label='Exit', command=self.destroy)
			menubar.add_cascade(label="File", menu=filemenu)
			self.master.config(menu=menubar)
		createMenu()

		self.platform = platform.system()
		if test:
			self.dataPath = os.path.join('.', '.chargeNumber')
		elif self.platform == 'Linux':
			self.dataPath = os.path.expanduser(os.path.join('~', '.chargeNumber'))
		elif self.platform == 'Darwin':
			self.dataPath = os.path.expanduser(os.path.join('~', '.chargeNumber'))
		elif self.platform == 'Windows':
			self.dataPath = os.path.expanduser(os.path.join('~', 'Appdata', 'Roaming', 'chargeNumber'))
		else:
			raise RuntimeError("Unknown Platform!")
		if not os.path.isdir(self.dataPath):
			os.mkdir(self.dataPath)

		self.tracker = HourTracker(self.dataPath)
		self.tracker.__enter__()

		self.htViewer = HourTrackerViewer(self.master, self.tracker)
		self.htViewer.grid(row=0, column=0, sticky=tk.NW)
		ProjectList(self.master, self.tracker).grid(row=0, column=1, sticky=tk.NW)

		self.master.bind('<Control-Shift-S>', self.arrive)
		self.master.mainloop()

	def arrive(self, *args):
		self.tracker.recordArrive()
		self.htViewer.update()

	def destroy(self):
		self.tracker.__exit__(None, None, None)
		self.master.destroy()

	def getHours(self):
		print(self.tracker.getHours(dt.datetime.today().date()))

if __name__ == '__main__':
	root = ChargeNumberTrackerApp()
	