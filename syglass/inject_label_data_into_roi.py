import sys
import numpy as np
import tifffile
import tkinter as tk
from tkinter import filedialog
import syglass as sy
#1 GB == 1600 secs

def predict(vol, roi_number):
	print("in prediction")
	model = models.Cellpose(gpu=True, model_type='cyto')

	masks, flows, styles, diams = model.eval(vol, diameter=None, channels=[2,2], do_3D=True, batch_size=1)
	#code.interact(local=locals())
	masks16 = masks.astype(np.uint16)
	tifffile.imsave('mask16_roi' + str(roi_number) + ".tiff", masks16)
	mask16_extra = masks16[..., np.newaxis]

	return mask16_extra
	
def get_roi_number():
	root=tk.Tk()
	mystring = tk.StringVar()
	def getvalue():
		global returnString 
		returnString = mystring.get()
		root.destroy()
	tk.Label(root, text="ROI #").grid(row=0)  #label
	tk.Entry(root, textvariable = mystring).grid(row=0, column=1) #entry textbox
	tk.WSignUp = tk.Button(root, text="Extract", command=getvalue).grid(row=3, column=0) #button
	root.mainloop()
	
def get_tiff_path():
	def getvalue():
		global returnString 
		returnString = mystring.get()
		root.destroy()
		
	def browseFiles():
		print('hello')
		global filename
		filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("Tiff files","*.tif*"), ("all files","*.*")))
		root.destroy()
	root=tk.Tk()
	mystring = tk.StringVar()
	tk.WSignUp = tk.Button(root, text="Choose File!", command=browseFiles).grid(row=3, column=0) #button
	root.mainloop()

def main(args):
	print("Inject Label Data into ROI Plugin, by Michael Morehead")
	print("Attempts to read a single 3D tiff, and inject it into the ROI")
	print("---------------------------------------")
	print("Usage: Highlight a project and use the Script Launcher in syGlass.")
	print("---------------------------------------")

	projectList = args["selected_projects"]

	doExtract = True
	if len(projectList) < 1:
		print("Highlight a project before running to select a project!")
		doExtract = False
	
	if len(projectList) > 1:
		print("This script only supports 1 project at a time, please select only one project before running.")
		doExtract = False

	if doExtract:
		get_roi_number()
		get_tiff_path()
		global returnString
		global filename
		print("Injecting file " + filename+ " into ROI " + str(returnString))
		project = projectList[0]
		data = tifffile.imread(filename)
		data = data[..., np.newaxis]
		print(data.shape)
		project.import_mask(data, int(returnString))

