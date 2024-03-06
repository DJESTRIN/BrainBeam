""" BrainBeamBase
The purpose of this script is to set up the basic classes and subsquent GUIs to run BrainBeam
"""
#import tkinter as tk
from tkinter import *
import tkinter as tk
import customtkinter as ctk
import subprocess, os
from threading import Thread
import subprocess
import webview 

ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BrainBeamGuiBase():
    def __init__(self):
        self.root=ctk.CTk()
        self.root.geometry("900x800+500+100")
        self.root.overrideredirect(True)
        self.close_button = ctk.CTkButton(self.root, text='X', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.03,anchor=CENTER)
        
        #Side Bar
        self.sidebar_frame = ctk.CTkFrame(self.root, width=200, height=1000, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.switch = ctk.CTkSwitch(master=self.sidebar_frame, text=f"Slurm",font=('Arial',15)).place(relx=0.95,rely=0.05,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Select Data", width =20,command=self.copydata).place(relx=0.95,rely=0.1,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Copy Data",width =8,command=self.copydata).place(relx=0.95,rely=0.15,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Denoise Data",width =8,command=self.copydata).place(relx=0.95,rely=0.20,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Stitch Data",width =8,command=self.copydata).place(relx=0.95,rely=0.25,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Convert Data to Neuroglancer",width =8,command=self.copydata).place(relx=0.95,rely=0.30,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Generate Training Data",width =8,command=self.copydata).place(relx=0.95,rely=0.35,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Convert data to Syglass",width =8,command=self.copydata).place(relx=0.95,rely=0.35,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Evalutate Classifier",width =8,command=self.copydata).place(relx=0.95,rely=0.35,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Apply CloudReg Registration",width =8,command=self.copydata).place(relx=0.95,rely=0.35,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Apply Ilastik Segmentation",width =8,command=self.copydata).place(relx=0.95,rely=0.40,anchor='e')
        self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Apply Custom Script",width =8,command=self.copydata).place(relx=0.95,rely=0.45,anchor='e')
        
        # Set up Tab page
        self.tabview = ctk.CTkTabview(self.root, width=500,height=700)
        self.tabview.place(relx=0.6, rely=0.5, anchor=CENTER)
        self.tabview.add("Overview")
        self.tabview.add("Copy")
        self.tabview.add("Denoise")
        self.tabview.add("Stitch")
        self.tabview.add("Neuroglancer conversion")
        self.tabview.add("Registration")
        self.tabview.add("Segmentation")
        self.tabview.add("Custom Script")
        self.tabview.tab("Overview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Copy").grid_columnconfigure(0, weight=1)


        
        # create textbox
        self.webbtn = ctk.CTkButton(self.tabview.tab("Neuroglancer conversion"),text="View in Neuroglancer",command=self.openneuroglancer)
        self.webbtn.place(relx=0.75,rely=0.1)
        self.webbtn.configure(state=DISABLED)

        self.set_up_custom_script()

    def set_up_custom_script(self):
        self.textbox = ctk.CTkTextbox(self.tabview.tab("Custom Script"), width=600,height=300)
        self.textbox.insert("0.0", "Implementing Custom Python Scripts in BrainBeam:\n\n" + "To run a custom python script you will need the full path to the sample or directory of samples. \n\n" +
                            "Please see our example python script (insert location here) in order to match our format. \n\n " +
                            "An example use case is to apply a custom neural network for image segmentation \n\n" +
                            "For each stitched sample, data will first be seperated into chunks as specified by you below. \n\n If left empty, the default chunk size is 500x500x500 pixels."+
                            "Once seperated, your function \n\n will be applied to each chunk. Then, each chunk will be stitched back together.\n\n The modified stitched files will then be saved in the directory of your choosing. \n\n" +
                            "For advanced use cases, please use our BrainBeam Command Line Interface (CLI)")
        self.textbox.place(relx=0.02,rely=0.01)
        self.optionmenu_1 = ctk.CTkOptionMenu(self.tabview.tab("Custom Script"), width=5,values=["Perform on Single Sample", "Perform on Batch of samples"])
        self.optionmenu_1.place(relx=0.35,rely=0.51)
        self.entry2 = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text="Full path to single sample's data or directory of samples. Please see our instructions for data org.")
        self.entry2.place(relx=0.02,rely=0.61)
        self.entry3 = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Full path to python script. Ex. C:\Users\mypython.py ")
        self.entry3.place(relx=0.02,rely=0.71)
        self.entry = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Set cubic volume size. Ex. '200' means stitched volume will be applied to 200x200x200 chunks.")
        self.entry.place(relx=0.02,rely=0.81)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Run Custom Script",width =8,state=DISABLED,command=self.copydata).place(relx=0.4,rely=0.91)

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