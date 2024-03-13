""" BrainBeamBase
The purpose of this script is to set up the basic classes and subsquent GUIs to run BrainBeam
"""
#import tkinter as tk
from tkinter import *
import tkinter as tk
import customtkinter as ctk
import subprocess, os, glob
from threading import Thread
import subprocess
import webview 
from PIL import Image
from tkinter import filedialog

ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BrainBeamGuiBase():
    def __init__(self):
        self.root=ctk.CTk()

        # trials
        # x = (self.root.winfo_screenwidth() / 2)
        # y = (self.root.winfo_screenheight() / 2)
        # self.root.geometry(f'{x}x{y}')
        # self.root.resizable(True, True)

        # self.root.geometry("1250x800+500+100")

        self.wd=os.getcwd()
        #self.root.overrideredirect(True)
        #self.close_button = ctk.CTkButton(self.root, text='Quit', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.03,anchor=CENTER)

        #Side Bar
        self.sidebar_frame = ctk.CTkFrame(self.root, width=180, height=1000, corner_radius=0)
        self.sidebar_frame.place(relx=0.00, rely=0.49, anchor=W)
        self.sidebar_frame.grid(row=0, column=0, pady=3, rowspan=4, sticky="w")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        #self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Start by Adding \n Lightsheet Data", width = 20,font=('Arial',15,'bold'),command=self.copydata).place(relx=0.85,rely=0.25,anchor='e')
    
        #Set up radio buttons
        self.set_up_radio_buttons()
        
        # Set up Tab page
        self.tabview = ctk.CTkTabview(self.root, width=1000,height=770)
        self.tabview.place(relx=0.57, rely=0.49, anchor=CENTER)
        self.tabview.grid(row=0, column=3, sticky="n")

        self.tabview.add("Overview")
        self.tabview.add("Copy, Move & Compress")
        self.tabview.add("Denoise")
        self.tabview.add("Stitch")
        self.tabview.add("Neuroglancer conversion")
        self.tabview.add("Registration")
        self.tabview.add("Segmentation")
        self.tabview.add("Custom Script")
        self.tabview.tab("Overview").grid_columnconfigure(10, weight=1)  # configure grid of individual tabs

        # create textbox
        self.webbtn = ctk.CTkButton(self.tabview.tab("Neuroglancer conversion"),text="View in Neuroglancer",command=self.openneuroglancer)
        self.webbtn.place(relx=0.75,rely=0.1)
        #self.webbtn.configure(state=DISABLED)

        self.set_up_custom_script()
        self.call_logo()
        self.set_up_overview()
        self.set_up_copy()

    def set_up_overview(self):
        #Set log image
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Create Project",font=("Arial",15,'bold'),command=self.set_up_samples)
        self.webbtn.place(relx=0.01,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Open Project",font=("Arial",15,'bold'),command=self.open_project)
        self.webbtn.place(relx=0.17,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Import New Data to Project",font=("Arial",15,'bold'),command=self.set_up_samples)
        self.webbtn.place(relx=0.33,rely=0.01)

    def open_project(self):
        json_file=filedialog.askopenfile(initialdir=self.wd,filetypes =[('Brain Beam Json Files', '*.json')])

    def set_up_samples(self):
        directory=self.select_folder()
        self.ystart=1
        if os.path.exists(os.path.join(directory,'lightsheet')):
            self.set_up_overview_headers()
            datapath=os.path.join(directory,"/lightsheet/raw") +'\*'
            self.samples=glob.glob(datapath)
            for sample in self.samples:
                samplename=os.path.basename(sample)
                self.samplelabel=ctk.CTkLabel(self.overview_frame,text=samplename,font=('Arial',15,'bold')).grid(row=self.ystart, column=0, padx=5, pady=5)
                self.set_up_overview_timeline()
                self.ystart+=1

        elif os.path.exists(os.path.join(directory,'Ex*')):
            self.set_up_overview_headers()
            sample=directory
            samplename=os.path.basename(sample)
            self.samplelabel=ctk.CTkLabel(self.overview_frame,text=samplename,font=('Arial',15,'bold')).grid(row=0, column=0, padx=5, pady=5)
            self.ystart+=1

        else:
            self.throw_error('The selected folder does \n not fit our format :( \n Select a new folder or reformat current folder \n please see our wiki on github.com')

    def set_up_overview_headers(self):
        self.overview_frame = ctk.CTkFrame(self.tabview.tab("Overview"), corner_radius=0,width=350,height=500)
        self.overview_frame.place(relx=0.01, rely=0.05)
        self.overview_frame.grid_rowconfigure(10, weight=1)
        self.overview_frame.grid_columnconfigure(22, weight=1)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Imported",font=('Arial',12,'bold')).grid(row=0, column=1, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Copied",font=('Arial',12,'bold')).grid(row=0, column=3, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Moved",font=('Arial',12,'bold')).grid(row=0, column=5, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Compressed",font=('Arial',12,'bold')).grid(row=0, column=7, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Converted",font=('Arial',12,'bold')).grid(row=0, column=9, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Denoised",font=('Arial',12,'bold')).grid(row=0, column=11, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Stitched",font=('Arial',12,'bold')).grid(row=0, column=13, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Precomputed",font=('Arial',12,'bold')).grid(row=0, column=15, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Registered",font=('Arial',12,'bold')).grid(row=0, column=17, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Segmented",font=('Arial',12,'bold')).grid(row=0, column=19, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Custom",font=('Arial',12,'bold')).grid(row=0, column=21, padx=5, pady=5)

    def set_up_overview_timeline(self):
        #Set log image
        image_path = os.path.join(os.getcwd(), "gui/images")
        self.errorimg = ctk.CTkImage(Image.open(os.path.join(image_path,"error.png")), size=(20, 20))
        self.completeimg = ctk.CTkImage(Image.open(os.path.join(image_path,"complete.png")), size=(20, 20))
        self.nextstepimg = ctk.CTkImage(Image.open(os.path.join(image_path,"nextstep.png")), size=(15, 7))
        self.pendingimg = ctk.CTkImage(Image.open(os.path.join(image_path,"pending.png")), size=(20, 20))
        self.runningimg = ctk.CTkImage(Image.open(os.path.join(image_path,"running.png")), size=(20, 20))
        #Set up overview frame
        # self.navigation_frame = ctk.CTkFrame(self.root, corner_radius=0,width=180,height=95)
        # self.navigation_frame.place(relx=0,rely=0.05)
        # self.navigation_frame.grid_rowconfigure(4, weight=1)

        for i in range(22):
            if ( i % 2 ) == 0: 
                if i==0 or i==22:
                    continue
                else:
                    self.navigation_frame_label = ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=self.nextstepimg).grid(row=self.ystart,column=i)
            else:
                self.navigation_frame_label = ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=self.pendingimg).grid(row=self.ystart,column=i)
        self.navigation_frame_label = ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=self.completeimg).grid(row=self.ystart,column=1)

    def select_folder(self):
        return filedialog.askdirectory(initialdir=self.wd)
 
    def throw_error(self,message):
        self.error=ctk.CTk()
        self.error.geometry("500x100")
        self.errmessage=ctk.CTkLabel(self.error,text=message).pack()
        self.error.mainloop()

    def set_up_copy(self):
        #Set up the copy/move/compress tab
        #Description
        self.textbox2 = ctk.CTkTextbox(self.tabview.tab("Copy, Move & Compress"), width=1000,height=50)
        self.textbox2.insert("0.0", "The following are basic copy, move and compress functions. However, in BrainBeam, we have attempted to "+
                            "Maximize the speed of copying by moving folders in parallel. \nThese functions are most effecient when running on " +
                            "A SLURM based HPC.")
        self.textbox2.place(relx=0.0005,rely=0.01)

        #Copy Data
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be copied.")
        self.entry2.place(relx=0.01,rely=0.15)
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be copied to.")
        self.entry2.place(relx=0.01,rely=0.2)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Copy Data to Another Folder",font=("Arial",15,'bold')).place(relx=0.01,rely=0.11)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.15)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.2)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Copying",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.82,rely=0.15)

        #Move Data
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Moved.")
        self.entry2.place(relx=0.01,rely=0.3)
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be Moved to.")
        self.entry2.place(relx=0.01,rely=0.35)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Move Data to Another Folder",font=("Arial",15,'bold')).place(relx=0.01,rely=0.26)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.3)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.35)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Moving",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.82,rely=0.3)

        #compress data
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Compressed.")
        self.entry2.place(relx=0.01,rely=0.45)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Compress Folder to tar.gz format",font=("Arial",15,'bold')).place(relx=0.01,rely=0.41)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.45)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Compressing",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.82,rely=0.45)

        #Decompress data
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input tar.gz file which will be Decompressed")
        self.entry2.place(relx=0.01,rely=0.55)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Decompress tar.gz file",font=("Arial",15,'bold')).place(relx=0.01,rely=0.51)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find tar.gz file",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.65,rely=0.55)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Decompressing",font=("Arial",15,'bold'),command=self.select_folder)
        self.webbtn.place(relx=0.82,rely=0.55)

        #Check processes
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Check status of code",font=("Arial",15,'bold'),command=self.select_folder,state=DISABLED)
        self.webbtn.place(relx=0.4,rely=0.75)

    def set_up_custom_script(self):
        self.textbox = ctk.CTkTextbox(self.tabview.tab("Custom Script"), width=1000,height=300)
        self.textbox.insert("0.0", "Implementing Custom Python Scripts in BrainBeam:\n\n" + "To run a custom python script you will need the full path to the sample or directory of samples." +
                            "Please see our example python script (insert location here) in order to match our format. \n\n " +
                            "An example use case is to apply a custom neural network for image segmentation" +
                            "For each stitched sample, data will first be seperated into chunks as specified by you below. \n\n If left empty, the default chunk size is 500x500x500 pixels."+
                            "Once seperated, your function will be applied to each chunk. Then, each chunk will be stitched back together.\n\n The modified stitched files will then be saved in the directory of your choosing." +
                            "For advanced use cases, please use our BrainBeam Command Line Interface (CLI)")
        self.textbox.place(relx=0.0005,rely=0.01)
        self.optionmenu_1 = ctk.CTkOptionMenu(self.tabview.tab("Custom Script"), width=5,values=["Perform on Single Sample", "Perform on Batch of samples"])
        self.optionmenu_1.place(relx=0.35,rely=0.51)
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text="Full path to single sample's data or directory of samples. Please see our instructions for data org.")
        self.entry2.place(relx=0.2,rely=0.61)
        self.entry3 = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Full path to python script. Ex. C:\Users\mypython.py ")
        self.entry3.place(relx=0.2,rely=0.71)
        self.entry = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Set cubic volume size. Ex. '200' means stitched volume will be applied to 200x200x200 chunks.")
        self.entry.place(relx=0.2,rely=0.81)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Run Custom Script",width =8,state=DISABLED,command=self.copydata).place(relx=0.6,rely=0.91)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Register Custom Script to Overview",width =8,state=DISABLED,command=self.copydata).place(relx=0.2,rely=0.91)

    def set_up_radio_buttons(self):
        # create radiobutton frame
        self.radio_var = tk.StringVar(value=0)
        self.label_radio_group = ctk.CTkLabel(master=self.sidebar_frame, text="Analysis Location:",font=('Arial',17,'bold'))
        self.label_radio_group.place(relx=0.9,rely=0.18,anchor='e')
        self.radio_button_1 = ctk.CTkRadioButton(master=self.sidebar_frame, text='LOCAL',font=('Arial',15,'bold'),variable=self.radio_var, value=0)
        self.radio_button_1.place(relx=0.68,rely=0.21,anchor='e')
        self.radio_button_2 = ctk.CTkRadioButton(master=self.sidebar_frame, text='SLURM HPC',font=('Arial',15,'bold'), variable=self.radio_var, value=1)
        self.radio_button_2.place(relx=0.78,rely=0.24,anchor='e')
        self.radio_button_3 = ctk.CTkRadioButton(master=self.sidebar_frame,text='AWS',font=('Arial',15,'bold'),variable=self.radio_var, value=2)
        self.radio_button_3.place(relx=0.68,rely=0.27,anchor='e')
    
    def call_logo(self):
        #Set log image
        image_path = os.path.join(self.wd, "gui/images")
        image_path = os.path.join(image_path,"BBlogoV1.png")
        self.logo_image = ctk.CTkImage(Image.open(image_path), size=(180, 90))

        self.navigation_frame = ctk.CTkFrame(self.root, corner_radius=0,width=180,height=95)
        self.navigation_frame.place(relx=0,rely=0.05)
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="", height=10,width=100, image=self.logo_image)
        self.navigation_frame_label.place(relx=0,rely=0.05)

    def __call__(self):
        self.refresh_screen()

    def refresh_screen(self):
        self.root.mainloop()
    
    def copydata(self):
        print('Copying data')

    def openneuroglancer(self):
        webview.create_window('BrainBeam', 'https://neuroglancer-demo.appspot.com/#!%7B%22layers%22:%5B%7B%22type%22:%22new%22%2C%22source%22:%22%22%2C%22tab%22:%22source%22%2C%22name%22:%22new%20layer%22%7D%5D%2C%22selectedLayer%22:%7B%22visible%22:true%2C%22layer%22:%22new%20layer%22%7D%2C%22layout%22:%224panel%22%7D')
        webview.start()


if __name__=='__main__':
    guioh=BrainBeamGuiBase()
    guioh()