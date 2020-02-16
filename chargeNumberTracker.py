#!/usr/bin/env python3

import tkinter as tk
import numpy as np
import datetime as dt
import json
import platform
import os
import tkcalendar as tkc
from tkinter import messagebox as tkMessageBox
import operator
import dataStore
import subprocess
import shlex
from tkinter import filedialog as tkf
import traceback
import glob

test = True


class Project():
    def __init__(self, name, chargeNumber, isBillable, sortIdx=-1):
        self.name = name
        self.chargeNumber = chargeNumber
        self.hours = {}
        self.isBillable = isBillable
        if sortIdx == -1:
            self.sortIdx = 999
        else:
            self.sortIdx = sortIdx

    def addHours(self, hours, date):
        assert(isinstance(hours, float) or isinstance(hours, dt.timedelta))
        if date not in self.hours:
            self.hours[date] = 0
        if isinstance(hours, float):
            self.hours[date] += hours
        elif isinstance(hours, dt.timedelta):
            self.hours[date] += hours.total_seconds() / 60.0 / 60.0

    def setHours(self, hours, date):
        assert(isinstance(hours, float) or isinstance(hours, dt.timedelta))
        if isinstance(hours, float):
            self.hours[date] = hours
        elif isinstance(hours, dt.timedelta):
            self.hours[date] = hours.total_seconds() / 60.0 / 60.0

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
    NUM_BACKUPS = 4

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
        data = dataStore.fromDict(data)
        self.dailyHours = data['dailyHours']
        self.projects = data['projects']
        self.timeRecord = data['timeRecord']
        self.prevTime = data['prevTime']
        self.arriveProject = data['arriveProject']
        self.recordHoursPath = data['recordHoursPath']

    def __exit__(self, exc_type, exc_value, tbk):
        self.flush()

    def flush(self):
        data = dataStore.toDict(dailyHours=self.dailyHours,
                                projects=self.projects, timeRecord=self.timeRecord,
                                recordHoursPath=self.recordHoursPath)
        existingBackups = glob.glob("%s.*" % (self.path))
        existingBackupNums = [(backup, int(os.path.basename(
            backup).split('.json.')[1])) for backup in existingBackups]
        if len(existingBackups) >= self.NUM_BACKUPS:
            os.remove(existingBackupNums[-1][0])
            existingBackupNums = existingBackupNums[0:-1]
        for backup, number in sorted(existingBackupNums, reverse=True, key=lambda x: x[1]):
            os.rename(backup, "%s.%d" % (self.path, number + 1))
        if os.path.isfile(self.path):
            os.rename(self.path, "%s.%d" % (self.path, 0))
        with open(self.path, 'w') as file:
            json.dump(data, file, indent=4, sort_keys=True)

    def registerAddProjectCallback(self, func):
        self.addProjectCallback.append(func)

    def registerAddHoursCallback(self, func):
        self.addHoursCallback.append(func)

    def getProjectNames(self, includeArrival=False):
        if includeArrival:
            return {project.name: project for project in self.projects}
        else:
            return {project.name: project for project in self.projects
                    if project.chargeNumber != "0"}

    def addProject(self, project):
        self.projects.append(project)
        for func in self.addProjectCallback:
            func(project)

    def __today(self):
        return self.timeRecord[dt.datetime.today().date()]

    def recordArrive(self, time=dt.datetime.now()):
        self.start = time
        self.prevTime = self.start
        self.timeRecord[dt.datetime.today().date()] = {}
        self.__today()[self.start] = self.arriveProject
        for func in self.addHoursCallback:
            func(self.arriveProject)
        self.flush()

    def addRecord(self, time, project):
        self.timeRecord[time.date()][time] = project

        # Update project hours
        timeRef = {}
        startTime = sorted(self.timeRecord[time.date()].keys())[0]
        for endTime in sorted(self.timeRecord[time.date()].keys())[1:]:
            if self.timeRecord[time.date()][endTime] not in timeRef:
                timeRef[self.timeRecord[time.date()][endTime]] = endTime - \
                    startTime
            else:
                timeRef[self.timeRecord[time.date()][endTime]] += endTime - \
                    startTime
            startTime = endTime
        for proj, tDelta in timeRef.items():
            proj.setHours(tDelta, time.date())
        if time > self.prevTime:
            self.prevTime = time
        for func in self.addHoursCallback:
            func(project)
        self.flush()

    def recordHours(self, project):
        time = dt.datetime.now()
        self.__today()[time] = project
        project.addHours(time - self.prevTime, time.date())
        self.prevTime = time
        for func in self.addHoursCallback:
            func(project)
        self.flush()

    def getTodayTotalHours(self):
        date = dt.datetime.now().date()
        totalHours = 0
        projectHours = self.getHours(date)
        for chargeNumber, hours in projectHours.items():
            totalHours += hours
        return totalHours

    def getTodayRemainingHours(self):
        return self.dailyHours - self.getTodayTotalHours()

    def getEarliestReleaseTime(self):
        if self.prevTime.date() != dt.datetime.now().date():
            return dt.datetime.now() + \
                dt.timedelta(hours=self.getTodayRemainingHours()) - \
                dt.timedelta(minutes=7.5)
        return self.prevTime + \
            dt.timedelta(hours=self.getTodayRemainingHours()) - \
            dt.timedelta(minutes=7.5)

    def getHours(self, date):
        retval = {}
        for project in self.projects:
            retval[project.chargeNumber] = project.getBillableHours(date)
        return retval


class HourTrackerViewer(tk.Frame):
    def __init__(self, master, hourTracker):
        self.hourTracker = hourTracker
        self.innerFrame = None
        self.nameMap = None
        self.projectNameIdx = 0
        self._displayedProjects = {}
        self.timeRecord = hourTracker.timeRecord

        super().__init__(master)

        self.__createWidget()
        self.hourTracker.registerAddProjectCallback(self.updateProject)

    def __createWidget(self):
        if self.innerFrame is not None:
            self.innerFrame.destroy()
        self.innerFrame = tk.Frame(self)
        self.dateSelector = tk.StringVar()
        dateEntry = tkc.DateEntry(self.innerFrame,
                                  textvariable=self.dateSelector, maxdate=dt.datetime.today())
        dateEntry.grid(row=0, column=0, columnspan=2)
        dateEntry.bind('<<DateEntrySelected>>', self.setDate)

        self.recordFrame = None
        self.setDate()

        self.projectSelector = tk.StringVar()
        self.nameMap = self.hourTracker.getProjectNames()
        self.projectNames = [project.name for project
                             in sorted(self.nameMap.values(),
                                       key=operator.attrgetter('sortIdx'))]
        if len(self.nameMap) > 0:
            self.projectSelector.set(self.projectNames[self.projectNameIdx])

        tk.OptionMenu(self.innerFrame, self.projectSelector,
                      *tuple(self.projectNames)).grid(row=2, column=0)
        button = tk.Button(self.innerFrame, text='Record',
                           command=self.recordActivity)
        button.grid(row=2, column=1)
        button.bind("<Up>", self.__changeProjectUp)
        button.bind("<Down>", self.__changeProjectDown)

        self.innerFrame.grid(row=0, column=0)

    def __changeProjectUp(self, *args):
        self.projectNameIdx -= 1
        if self.projectNameIdx < 0:
            self.projectNameIdx = 0
        self.projectSelector.set(self.projectNames[self.projectNameIdx])

    def __changeProjectDown(self, *args):
        self.projectNameIdx += 1
        if self.projectNameIdx >= len(self.projectNames):
            self.projectNameIdx = len(self.projectNames) - 1
        self.projectSelector.set(self.projectNames[self.projectNameIdx])

    def updateProject(self, project):
        self.__createWidget()

    def update(self):
        self.__createWidget()

    def recordActivity(self):
        projectName = self.projectSelector.get()
        project = self.nameMap[projectName]
        try:
            self.hourTracker.recordHours(project)
        except KeyError:
            tkMessageBox.showerror(
                'Entry Error', 'Error: Start time not found!')
            return
        self.projectSelector.set(self.projectNames[0])
        self.innerFrame.destroy()
        self.innerFrame = tk.Frame(self)
        self.__createWidget()

    def setDate(self, *args):
        if self.recordFrame is not None:
            self.recordFrame.destroy()
            self._displayedProjects = {}
        self.recordFrame = tk.Frame(self.innerFrame)
        date = dt.datetime.strptime(self.dateSelector.get(), '%m/%d/%y').date()
        if date in self.hourTracker.timeRecord:
            row = 0
            for record in sorted(self.hourTracker.timeRecord[date].items()):
                timeLabel = tk.Label(self.recordFrame, text=record[0].strftime(
                    '%H:%M'))
                timeLabel.grid(row=row, column=0)
                projectLabel = tk.Label(self.recordFrame, text=record[1].name)
                projectLabel.grid(row=row, column=1)
                projectLabel.bind('<Double-Button-1>',
                                  self.__editChargeNumberHandler)
                self._displayedProjects[projectLabel] = [
                    record[0], timeLabel, record[1], self.hourTracker.timeRecord[date]]
                row += 1
        self.recordFrame.grid(row=1, column=0, columnspan=2)

    def __editChargeNumberHandler(self, event: tk.Event):
        timestamp, timeLabel, project, projectTree = self._displayedProjects[event.widget]
        d = TimeEditor(self, self.hourTracker.getProjectNames(includeArrival=True), title='Edit Time',
                       time=self._displayedProjects[event.widget][0], project=project)
        if d.result:
            if d.result[1] != project and d.result[0] == timestamp:
                #                 Just need to update the charge number
                projectTree[timestamp] = d.result[1]
            elif d.result[0] != timestamp and d.result[1] == project:
                #                 Adjusting the time
                projectTree.pop(timestamp, None)
                projectTree[d.result[0]] = project
            else:
                #                 Adjusting time and charge number
                projectTree.pop(timestamp, None)
                projectTree[d.result[0]] = d.result[1]
            self.update()


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
        for project in sorted(self.hourTracker.projects, key=operator.attrgetter('sortIdx')):
            if project.chargeNumber != "0":
                tk.Label(self.innerFrame, text=project.name,
                         anchor=tk.NW).grid(row=row, column=0)
                tk.Label(self.innerFrame, text='%s' % (
                    project.chargeNumber), anchor=tk.NW).grid(row=row, column=1)

                billableHours = project.getBillableHours(today)
                if billableHours > 0:
                    tk.Label(self.innerFrame, text='%.2f hrs' % (
                        billableHours), anchor=tk.NW).grid(row=row, column=2)
                else:
                    tk.Label(self.innerFrame, text="").grid(row=row, column=2)
                row += 1

        self.projectEntry = tk.StringVar()
        self.chargeNumberEntry = tk.StringVar()
        tk.Entry(self.innerFrame, textvariable=self.projectEntry).grid(
            row=row, column=0)
        entry = tk.Entry(self.innerFrame, textvariable=self.chargeNumberEntry)
        entry.grid(row=row, column=1)
        entry.bind('<Return>', self.addProject)
        entry.bind('<KP_Enter>', self.addProject)
        button = tk.Button(self.innerFrame, text='Add Project',
                           command=self.addProject)
        button.grid(row=row, column=2)
        button.bind('<Return>', self.addProject)
        button.bind('<KP_Enter>', self.addProject)

        tk.Label(self.innerFrame, text="Total Hours: %.2f" % (
            self.hourTracker.getTodayTotalHours()), anchor=tk.NW).grid(row=0, column=3)
        earliestReleaseTime = self.hourTracker.getEarliestReleaseTime()
        tk.Label(self.innerFrame, text="Earliest Off Time: %s" % (self.hourTracker.getEarliestReleaseTime(
        ).time().strftime('%H:%M')), anchor=tk.NW).grid(row=1, column=3)

        self.innerFrame.grid(row=0, column=0)

    def addProject(self, *args):
        self.hourTracker.addProject(
            Project(self.projectEntry.get(), self.chargeNumberEntry.get(), True))
        self.projectEntry.set("")
        self.chargeNumberEntry.set('')
        self.createWidget()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, hour_tracker):
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        self.title("Settings")
        self.parent = parent
        self.hour_tracker = hour_tracker

        self.recordHoursPath = tk.StringVar()
        self.recordHoursPath.set(self.hour_tracker.recordHoursPath)

        self.bodyFrame = None
        self.initial_focus = self.createBody()

        self.acceptFrame = None
        self.createAcceptFrame()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    def createBody(self):
        if self.bodyFrame is not None:
            self.bodyFrame.destroy()
        self.bodyFrame = tk.Frame(self)
        tk.Label(self.bodyFrame, text="Hour Log App:").grid(row=0, column=0)
        entry = tk.Entry(self.bodyFrame, textvariable=self.recordHoursPath).grid(
            row=0, column=1)
        tk.Button(self.bodyFrame, text='...',
                  command=self.getRecordHoursPath).grid(row=0, column=2)

        self.bodyFrame.grid(row=0, column=0)

    def getRecordHoursPath(self):
        if self.recordHoursPath.get() is "":
            if platform.system() == "Linux":
                init_path = "/usr/local/bin"
            else:
                init_path = "C:\\Program Files"
        else:
            init_path = os.path.dirname(self.recordHoursPath.get())
        newPath = tkf.askopenfilename(initialdir=init_path, parent=self)
        self.recordHoursPath.set(newPath)

    def createAcceptFrame(self):
        if self.acceptFrame is not None:
            self.acceptFrame.destroy()
        self.acceptFrame = tk.Frame(self)
        tk.Button(self.acceptFrame, text="OK",
                  command=self.ok).grid(row=0, column=0)
        tk.Button(self.acceptFrame, text='Cancel',
                  command=self.cancel).grid(row=0, column=1)
        self.acceptFrame.grid(row=1, column=0)

    def cancel(self, event=None):
        self.parent.focus_set()
        self.destroy()

    def validate(self):
        try:
            assert(os.path.isfile(self.recordHoursPath.get()))
            return True
        except:
            return False

    def ok(self, event=None):
        if not self.validate():
            return
        self.withdraw()
        self.update_idletasks()

        # apply changes
        self.hour_tracker.recordHoursPath = self.recordHoursPath.get()

        self.cancel()


class TimeEditor(tk.Toplevel):
    def __init__(self, parent, projects, title=None, time=dt.datetime.now(), project=None):
        tk.Toplevel.__init__(self,  parent)
        self.transient(parent)

        if title:
            self.title(title)
        else:
            self.title("Custom Time")

        self.parent = parent

        self.result = None
        self.projects = projects
        self.time = time

        body = tk.Frame(self)
        self.dateSelector = tk.StringVar()
        self.hrSelector = tk.StringVar()
        self.hrSelector.set(time.hour)
        self.minSelector = tk.StringVar()
        self.minSelector.set(time.minute)
        self.projectSelector = tk.StringVar()
        self.projectNames = [project.name for project
                             in sorted(self.projects.values(),
                                       key=operator.attrgetter('chargeNumber'))]
        if project is None:
            self.projectNameIdx = 0
        else:
            self.projectNameIdx = self.projectNames.index(project.name)

        self.initial_focus = self.create(body)
        body.grid(row=0, column=0, padx=5, pady=5)

        buttonbox = tk.Frame(self)
        submitButton = tk.Button(buttonbox, text='Submit', width=10,
                                 command=self.ok)
        submitButton.grid(row=0, column=0, padx=5, pady=5)
        cancelButton = tk.Button(buttonbox, text='Cancel', width=10,
                                 command=self.cancel)
        cancelButton.grid(row=0, column=1, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        buttonbox.grid(row=1, column=0)

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()
        self.grab_set()

        self.wait_window(self)

    def create(self, parent):
        self.dateEntry = tkc.DateEntry(parent, textvariable=self.dateSelector,
                                       maxdate=self.time)
        self.dateEntry.grid(row=0, column=0, columnspan=2)
        hr = tk.Spinbox(parent, from_=-1, to=24, textvariable=self.hrSelector,
                        width=5)
        hr.grid(row=1, column=0)
        min_ = tk.Spinbox(parent, from_=-1, to=60, textvariable=self.minSelector,
                          width=5, command=self.rotateMin)
        min_.grid(row=1, column=1)
        if len(self.projects) > 0:
            self.projectSelector.set(self.projectNames[self.projectNameIdx])
        tk.OptionMenu(parent, self.projectSelector, *tuple(self.projectNames))\
            .grid(row=2, column=0, columnspan=2)

    def rotateMin(self):
        if self.minSelector.get() == "-1":
            self.minSelector.set("59")
            hr = int(self.hrSelector.get()) - 1
            if hr == -1:
                hr = 23
                date = dt.datetime.strptime(
                    self.dateSelector.get(), '%m/%d/%y')
                date = date.replace(day=date.day - 1)
                self.dateSelector.set(date.strftime('%m/%d/%y'))
            self.hrSelector.set(str(hr))
        elif self.minSelector.get() == "60":
            self.minSelector.set('0')
            hr = int(self.hrSelector.get()) + 1
            self.hrSelector.set(str(hr))
            if hr == 24:
                hr = 0
                date = dt.datetime.strptime(
                    self.dateSelector.get(), '%m/%d/%y')
                date = date.replace(day=date.day + 1)
                self.dateSelector.set(date.strftime('%m/%d/%y'))
            self.hrSelector.set(str(hr))

    def ok(self, event=None):

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    def apply(self):
        date = dt.datetime.strptime(self.dateSelector.get(), '%m/%d/%y')
        hr = int(self.hrSelector.get())
        min_ = int(self.minSelector.get())
        date = date.replace(hour=hr)
        date = date.replace(minute=min_)
        self.result = date, self.projects[self.projectSelector.get()]


class ChargeNumberTrackerApp:
    def __init__(self):
        self.platform = platform.system()
        if test:
            self.dataPath = os.path.join('.', 'chargeNumber')
        elif self.platform == 'Linux':
            self.dataPath = os.path.expanduser(
                os.path.join('~', '.chargeNumber'))
        elif self.platform == 'Darwin':
            self.dataPath = os.path.expanduser(
                os.path.join('~', '.chargeNumber'))
        elif self.platform == 'Windows':
            self.dataPath = os.path.expanduser(os.path.join('~', 'Appdata',
                                                            'Roaming', 'chargeNumber'))
        else:
            raise RuntimeError("Unknown Platform!")
        if not os.path.isdir(self.dataPath):
            os.mkdir(self.dataPath)

        self.tracker = HourTracker(self.dataPath)

        try:
            self.tracker.__enter__()
        except Exception as e:
            print(traceback.print_last())
            if tkMessageBox.askyesno("Charge Number Hour Tracker", "Failed to "
                                     "load data - would you like to delete the old data?"):
                try:
                    os.remove(self.tracker.path)
                except:
                    pass
                self.tracker.__enter__()
            else:
                return

        self.master = tk.Tk()
        self.master.protocol("WM_DELETE_WINDOW", self.destroy)

        self.master.title('Charge Number Hour Tracker')
        self.menubar = None

        self.createMenu()

        self.htViewer = HourTrackerViewer(self.master, self.tracker)
        self.htViewer.grid(row=0, column=0, sticky=tk.NW)
        ProjectList(self.master, self.tracker).grid(
            row=0, column=1, sticky=tk.NW)

        self.master.bind('<Control-Shift-S>', self.arrive)
        self.master.mainloop()

    def createMenu(self):
        if self.menubar:
            self.menubar.destroy()
        self.menubar = tk.Menu(self.master)
        filemenu = tk.Menu(self.menubar, tearoff=0)
        filemenu.add_command(label='Arrive', command=self.arrive)
        filemenu.add_command(label='Get Hours', command=self.getHours)
        filemenu.add_command(label='Record Custom...',
                             command=self.recordCustom)
        filemenu.add_separator()
        filemenu.add_command(label='Preferences', command=self.setPrefs)
        filemenu.add_separator()
        filemenu.add_command(label='Log Hours', command=self.logHours,
                             state=("disabled" if self.tracker.recordHoursPath is "" else "normal"))
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command=self.destroy)
        self.menubar.add_cascade(label="File", menu=filemenu)
        self.master.config(menu=self.menubar)

    def logHours(self):
        excPath = self.tracker.recordHoursPath
        if excPath is not "":
            if platform.system() == 'Linux':
                subprocess.Popen(shlex.split(excPath))
            elif platform.system() == 'Windows':
                subprocess.Popen(shlex.split(excPath, posix=False), shell=True)

    def arrive(self, *args):
        self.tracker.recordArrive()
        self.htViewer.update()

    def destroy(self):
        self.tracker.__exit__(None, None, None)
        self.master.destroy()

    def getHours(self):
        print(self.tracker.getHours(dt.datetime.today().date()))

    def recordCustom(self):
        d = TimeEditor(
            self.master, self.tracker.getProjectNames(includeArrival=True))
        if d.result:
            if d.result[1] == self.tracker.arriveProject:
                self.tracker.recordArrive(d.result[0])
            else:
                self.tracker.addRecord(*d.result)
            self.htViewer.update()

    def setPrefs(self):
        d = SettingsDialog(self.master, self.tracker)
        self.createMenu()


if __name__ == '__main__':
    root = ChargeNumberTrackerApp()
