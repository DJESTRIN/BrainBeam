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
from PIL import Image

ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BrainBeamGuiBase():
    def __init__(self):
        self.root=ctk.CTk()
        self.root.geometry("900x800+500+100")
        self.root.overrideredirect(True)
        self.close_button = ctk.CTkButton(self.root, text='Quit', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.03,anchor=CENTER)

        #Side Bar
        self.sidebar_frame = ctk.CTkFrame(self.root, width=180, height=1000, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        #self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Start by Adding \n Lightsheet Data", width = 20,font=('Arial',15,'bold'),command=self.copydata).place(relx=0.85,rely=0.25,anchor='e')
    
        #Set up radio buttons
        self.set_up_radio_buttons()
        
        # Set up Tab page
        self.tabview = ctk.CTkTabview(self.root, width=500,height=700)
        self.tabview.place(relx=0.6, rely=0.5, anchor=CENTER)
        self.tabview.add("Overview")
        self.tabview.add("Copy/Move")
        self.tabview.add("Denoise")
        self.tabview.add("Stitch")
        self.tabview.add("Neuroglancer conversion")
        self.tabview.add("Registration")
        self.tabview.add("Segmentation")
        self.tabview.add("Custom Script")
        self.tabview.tab("Overview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs

        # create textbox
        self.webbtn = ctk.CTkButton(self.tabview.tab("Neuroglancer conversion"),text="View in Neuroglancer",command=self.openneuroglancer)
        self.webbtn.place(relx=0.75,rely=0.1)
        self.webbtn.configure(state=DISABLED)

        self.set_up_custom_script()
        self.call_logo()
        self.set_up_overview()

    def set_up_overview(self):
        #Set log image
        print('here')

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
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Run Custom Script",width =8,state=DISABLED,command=self.copydata).place(relx=0.6,rely=0.91)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Register Custom Script to Overview",width =8,state=DISABLED,command=self.copydata).place(relx=0.2,rely=0.91)

    def set_up_radio_buttons(self):
        # create radiobutton frame
        self.radio_var = tk.StringVar(value=0)
        self.label_radio_group = ctk.CTkLabel(master=self.sidebar_frame, text="Set Analysis location:",font=('Arial',15,'bold'))
        self.label_radio_group.place(relx=0.9,rely=0.3,anchor='e')
        self.radio_button_1 = ctk.CTkRadioButton(master=self.sidebar_frame, text='Local Computer',font=('Arial',15,'bold'),variable=self.radio_var, value=0)
        self.radio_button_1.place(relx=0.9,rely=0.33,anchor='e')
        self.radio_button_2 = ctk.CTkRadioButton(master=self.sidebar_frame, text='SLURM HPC',font=('Arial',15,'bold'), variable=self.radio_var, value=1)
        self.radio_button_2.place(relx=0.78,rely=0.36,anchor='e')
        self.radio_button_3 = ctk.CTkRadioButton(master=self.sidebar_frame,text='AWS',font=('Arial',15,'bold'),variable=self.radio_var, value=2)
        self.radio_button_3.place(relx=0.68,rely=0.39,anchor='e')
    
    def call_logo(self):
        #Set log image
        image_path = os.path.join(os.getcwd(), "gui")
        image_path = os.path.join(image_path, "images")
        image_path = os.path.join(image_path,"BBlogoV1.png")
        print(image_path)
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