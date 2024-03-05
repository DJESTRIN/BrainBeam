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
        self.root.geometry("1200x1000+500+10")
        self.root.overrideredirect(True)
        self.close_button = ctk.CTkButton(self.root, text='X', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.05,anchor=CENTER)
        
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
        
        #
        self.tabview = ctk.CTkTabview(self.root, width=500,height=700)
        self.tabview.place(relx=0.55, rely=0.4, anchor=CENTER)
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


        #
        # create textbox
        self.textbox = ctk.CTkLabel(self.tabview.tab("Stitch"),text="dave is finished")
        self.textbox.place(relx=0,rely=0.5)


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