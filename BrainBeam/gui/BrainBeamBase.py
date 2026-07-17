""" BrainBeamBase
The purpose of this script is to set up the basic classes and subsquent GUIs to run BrainBeam
"""
import tkinter as tk
import customtkinter as ctk
import os, glob
import threading
from PIL import Image
from tkinter import filedialog
import json

from BrainBeamCLI import API, PipelineError

ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BrainBeamGuiBase():
    def __init__(self):
        self.root=ctk.CTk()
        self.root.geometry("1250x900+500+100")
        self.wd=os.getcwd()
        self.index=0
        #self.root.overrideredirect(True)
        #self.close_button = ctk.CTkButton(self.root, text='Quit', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.03,anchor=CENTER)

        #Side Bar
        self.sidebar_frame = ctk.CTkFrame(self.root, width=180, height=1000, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        #self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Start by Adding \n Lightsheet Data", width = 20,font=('Arial',15,'bold'),command=self.copydata).place(relx=0.85,rely=0.25,anchor='e')
    
        #Set up radio buttons
        self.set_up_radio_buttons()
        
        # Set up Tab page
        self.tabview = ctk.CTkTabview(self.root, width=1000,height=800)
        self.tabview.place(relx=0.57, rely=0.49, anchor=tk.CENTER)
        self.tabview.add("Overview")
        self.tabview.add("Copy, Move & Compress")
        self.tabview.add("Denoise")
        self.tabview.add("Stitch")
        self.tabview.add("Registration")
        self.tabview.add("Segmentation")
        self.tabview.add("Custom Script")
        self.tabview.tab("Overview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs

        self.set_up_custom_script()
        self.call_logo()
        self.set_up_overview()
        self.set_up_copy()

    def get_project_file_path(self):
        if self.projectfiledir.endswith('.json'):
            return self.projectfiledir
        return f'{self.projectfiledir}.json'

    def set_up_overview(self):
        #Set log image
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Create Project",font=("Arial",15,'bold'),command=self.set_up_project)
        self.webbtn.place(relx=0.01,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Open Project",font=("Arial",15,'bold'),command=self.open_project)
        self.webbtn.place(relx=0.17,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Import New Data to Project",font=("Arial",15,'bold'),command=self.AddNewData)
        self.webbtn.place(relx=0.33,rely=0.01)

    def open_project(self):
        # Open a Brain Beam JSON project file
        self.projectfiledir=filedialog.askopenfilename(initialdir=self.wd,filetypes =[('json', '*.json')])
        with open(self.projectfiledir, 'r') as openfile:
            self.overviewdict = json.load(openfile)
            self.index=len(self.overviewdict)

        self.updateoverview()

    def AddNewData(self):
        # Add New data to a currently opened project
        try: #Open new directory with new data
            if len(self.overviewdict)>0:
                directory=self.select_folder('Please select folder containing NEW lightsheet data! Note, please see our wiki regarding data formating')
                self.add_folders_to_dict(directory)
                self.updateoverview() 

        except AttributeError:
            self.throw_error('Please open or create a project before adding new data')

    def set_up_project(self):
        #Get Project file info from user
        self.projectfiledir=filedialog.asksaveasfilename(title="Please save Project File",initialdir=self.wd,filetypes =[('json', '.json')])

        #Open folder containing the new data
        directory=self.select_folder('Please select folder containing lightsheet data! Note, please see our wiki regarding dataformating') # get the directory
        self.add_folders_to_dict(directory)
        self.updateoverview()
    
    def add_folders_to_dict(self,directory):
        if self.index==0:
            self.overviewdict={}
        if os.path.exists(os.path.join(directory,'lightsheet')): # If it is a folder containing samples
            # Search for samples in folder
            datapath=os.path.join(directory,"lightsheet")
            datapath=os.path.join(datapath,"raw") +'/*'
            self.samples=glob.glob(datapath)

            #Loop through folder and add new sample data
            for i,sample in enumerate(self.samples):
                samplename=os.path.basename(sample)
                foldername = os.path.basename(directory)    # Get directory name
                dict_oh={'parentfoldername':foldername,'samplename':samplename,'Imported':'complete','Copied':'pending', 'Moved':'pending','Compressed':'pending','Converted':'pending',
                         'Denoise':'pending','Stitch':'pending','Registration':'pending','Segmentation':'pending','Custom Script':'pending','rawpath':sample}
                self.overviewdict[self.index]=dict_oh
                self.index+=1
        elif 'ex' in os.path.basename(directory).lower(): #When selecting a simple folder for with one sample
            samplename=os.path.basename(directory)
            foldername=None
            dict_oh={'parentfoldername':foldername,'samplename':samplename,'Imported':'complete','Copied':'pending', 'Moved':'pending','Compressed':'pending','Converted':'pending',
                         'Denoise':'pending','Stitch':'pending','Registration':'pending','Segmentation':'pending','Custom Script':'pending','rawpath':directory}
            self.overviewdict[self.index]=dict_oh
            self.index+=1
        else: #Input folder does not fit our format
            self.throw_error('The selected folder does \n not fit our format :( \n Select a new folder or reformat current folder \n please see our wiki on github.com')
        
        # Save json dictionary for project to a file. 
        try:
            #Write json into a file
            self.overviewdict=json.dumps(self.overviewdict,indent=4)
            with open(self.get_project_file_path(), "w") as outfile:
                outfile.write(self.overviewdict)
            
            with open(self.get_project_file_path(), 'r') as openfile:
                self.overviewdict = json.load(openfile)
        except AttributeError:
            self.throw_error('The Project file was not created')
        
    def updateoverview(self):
        self.set_up_overview_headers()

        #Set up gui images path
        image_path = os.path.join(self.wd, "BrainBeam", "gui", "images")
        self.errorimg = ctk.CTkImage(Image.open(os.path.join(image_path,"error.png")), size=(20, 20))
        self.completeimg = ctk.CTkImage(Image.open(os.path.join(image_path,"complete.png")), size=(20, 20))
        self.nextstepimg = ctk.CTkImage(Image.open(os.path.join(image_path,"nextstep.png")), size=(15, 7))
        self.pendingimg = ctk.CTkImage(Image.open(os.path.join(image_path,"pending.png")), size=(20, 20))
        self.runningimg = ctk.CTkImage(Image.open(os.path.join(image_path,"running.png")), size=(20, 20))

        # Destroy previously made images if any
        try:
            for label in self.all_overview_images:
                label.destroy() 
        except AttributeError:
            self.all_overview_images=[]

        row_oh=1
        for sample in self.overviewdict:
            dict_oh=self.overviewdict[sample]
            for key,value in dict_oh.items():
                #Determine value of the key
                if value=='pending':
                    image_oh=self.pendingimg
                elif value=='complete':
                    image_oh=self.completeimg
                elif value=='error':
                    image_oh=self.errorimg
                elif value=='running':
                    image_oh=self.runningimg

                #generate image
                if key=='samplename':
                    label=ctk.CTkLabel(self.overview_frame, text=value, font=('Arial',10,'bold')).grid(row=row_oh,column=1)
                if key=='Imported':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=3)
                if key=='Copied':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=5)
                if key=='Moved':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=7)
                if key=='Compressed':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=9)
                if key=='Converted':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=11)
                if key=='Denoise':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=13)
                if key=='Stitch':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=15)
                if key=='Registration':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=17)
                if key=='Segmentation':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=19)
                if key=='Custom Script':
                    label=ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=image_oh).grid(row=row_oh,column=21)

                #Put labels in a common list
                try:
                    self.all_overview_images.append(label)
                except:
                    continue
            row_oh+=1

        for row_oh in range(len(self.overviewdict)):
            for i in range(21):
                if ( i % 2 ) == 0: 
                    if i==0 or i==2:
                        continue
                    self.navigation_frame_label = ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=self.nextstepimg).grid(row=row_oh+1,column=i)
     

    def set_up_overview_headers(self):
        if hasattr(self, 'overview_frame'):
            self.overview_frame.destroy()
        self.overview_frame = ctk.CTkFrame(self.tabview.tab("Overview"), corner_radius=0,width=350,height=500)
        self.overview_frame.place(relx=0.01, rely=0.05)
        self.overview_frame.grid_rowconfigure(len(self.overviewdict)+2, weight=1)
        self.overview_frame.grid_columnconfigure(21, weight=1)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Imported",font=('Arial',12,'bold')).grid(row=0, column=3, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Copied",font=('Arial',12,'bold')).grid(row=0, column=5, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Moved",font=('Arial',12,'bold')).grid(row=0, column=7, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Compressed",font=('Arial',12,'bold')).grid(row=0, column=9, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Converted",font=('Arial',12,'bold')).grid(row=0, column=11, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Denoised",font=('Arial',12,'bold')).grid(row=0, column=13, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Stitched",font=('Arial',12,'bold')).grid(row=0, column=15, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Registered",font=('Arial',12,'bold')).grid(row=0, column=17, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Segmented",font=('Arial',12,'bold')).grid(row=0, column=19, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Custom",font=('Arial',12,'bold')).grid(row=0, column=21, padx=5, pady=5)

    def select_folder(self,label='Open Folder'):
        return filedialog.askdirectory(title=label,initialdir=self.wd)

    def select_folder_into_entry(self,entry,label='Open Folder'):
        folder=self.select_folder(label=label)
        if folder:
            entry.delete(0,tk.END)
            entry.insert(0,folder)
        return folder

    def throw_error(self,message):
        self.error=ctk.CTk()
        self.error.geometry("500x100")
        self.errmessage=ctk.CTkLabel(self.error,text=message).pack()
        self.error.mainloop()

    def get_computertype(self):
        #Radio button values: 0=Local, 1=SLURM HPC, 2=AWS
        mapping={'0':'local','1':'slurm','2':'aws'}
        return mapping.get(str(self.radio_var.get()),'local')

    def run_backend_action(self,status_label,action_name,action):
        #Runs a BrainBeamCLI.API call on a background thread so the GUI does not freeze,
        #then marshals the status label update back onto the Tkinter main thread.
        def update_label(text):
            self.root.after(0,lambda: status_label.configure(text=text))
        def worker():
            update_label(f"{action_name}: running...")
            try:
                api=API(self.get_computertype())
                action(api)
                update_label(f"{action_name}: complete.")
            except (PipelineError, NotImplementedError, ValueError, FileNotFoundError) as e:
                update_label(f"{action_name} failed: {e}")
        threading.Thread(target=worker,daemon=True).start()

    def set_up_copy(self):
        #Set up the copy/move/compress tab
        #Description
        self.textbox2 = ctk.CTkTextbox(self.tabview.tab("Copy, Move & Compress"), width=1000,height=50)
        self.textbox2.insert("0.0", "The following are basic copy, move and compress functions. However, in BrainBeam, we have attempted to "+
                            "Maximize the speed of copying by moving folders in parallel. \nThese functions are most effecient when running on " +
                            "A SLURM based HPC.")
        self.textbox2.place(relx=0.0005,rely=0.01)

        #Copy Data
        self.copy_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be copied.")
        self.copy_input_entry.place(relx=0.01,rely=0.15)
        self.copy_output_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be copied to.")
        self.copy_output_entry.place(relx=0.01,rely=0.2)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Copy Data to Another Folder",font=("Arial",15,'bold')).place(relx=0.01,rely=0.11)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.copy_input_entry,'Select folder to copy'))
        self.webbtn.place(relx=0.65,rely=0.15)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.copy_output_entry,'Select destination folder'))
        self.webbtn.place(relx=0.65,rely=0.2)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Copying",font=("Arial",15,'bold'),command=self.start_copy)
        self.webbtn.place(relx=0.82,rely=0.15)
        self.copy_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=("Arial",11))
        self.copy_status_label.place(relx=0.01,rely=0.24)

        #Move Data
        self.move_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Moved.")
        self.move_input_entry.place(relx=0.01,rely=0.3)
        self.move_output_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be Moved to.")
        self.move_output_entry.place(relx=0.01,rely=0.35)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Move Data to Another Folder",font=("Arial",15,'bold')).place(relx=0.01,rely=0.26)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.move_input_entry,'Select folder to move'))
        self.webbtn.place(relx=0.65,rely=0.3)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.move_output_entry,'Select destination folder'))
        self.webbtn.place(relx=0.65,rely=0.35)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Moving",font=("Arial",15,'bold'),command=self.start_move)
        self.webbtn.place(relx=0.82,rely=0.3)
        self.move_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=("Arial",11))
        self.move_status_label.place(relx=0.01,rely=0.39)

        #compress data
        self.compress_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Compressed.")
        self.compress_input_entry.place(relx=0.01,rely=0.45)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Compress Folder to tar.gz format",font=("Arial",15,'bold')).place(relx=0.01,rely=0.41)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.compress_input_entry,'Select folder to compress'))
        self.webbtn.place(relx=0.65,rely=0.45)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Compressing",font=("Arial",15,'bold'),command=self.start_compress)
        self.webbtn.place(relx=0.82,rely=0.45)
        self.compress_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=("Arial",11))
        self.compress_status_label.place(relx=0.01,rely=0.49)

        #Decompress data
        self.decompress_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing .tar.gz archives which will be Decompressed")
        self.decompress_input_entry.place(relx=0.01,rely=0.55)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Decompress tar.gz archives",font=("Arial",15,'bold')).place(relx=0.01,rely=0.51)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=("Arial",15,'bold'),command=lambda: self.select_folder_into_entry(self.decompress_input_entry,'Select folder containing .tar.gz archives'))
        self.webbtn.place(relx=0.65,rely=0.55)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Decompressing",font=("Arial",15,'bold'),command=self.start_decompress)
        self.webbtn.place(relx=0.82,rely=0.55)
        self.decompress_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=("Arial",11))
        self.decompress_status_label.place(relx=0.01,rely=0.59)

        #Check processes
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Check status of code",font=("Arial",15,'bold'),command=self.select_folder,state=tk.DISABLED)
        self.webbtn.place(relx=0.4,rely=0.75)

    def start_copy(self):
        input_dir=self.copy_input_entry.get().strip()
        output_dir=self.copy_output_entry.get().strip()
        if not input_dir or not output_dir:
            self.throw_error('Please select both an input and output folder before copying.')
            return
        self.run_backend_action(self.copy_status_label,'Copy',lambda api: api.copy(input_dir,output_dir))

    def start_move(self):
        input_dir=self.move_input_entry.get().strip()
        output_dir=self.move_output_entry.get().strip()
        if not input_dir or not output_dir:
            self.throw_error('Please select both an input and output folder before moving.')
            return
        self.run_backend_action(self.move_status_label,'Move',lambda api: api.move(input_dir,output_dir))

    def start_compress(self):
        input_dir=self.compress_input_entry.get().strip()
        if not input_dir:
            self.throw_error('Please select a folder to compress.')
            return
        self.run_backend_action(self.compress_status_label,'Compress',lambda api: api.compress(input_dir))

    def start_decompress(self):
        input_dir=self.decompress_input_entry.get().strip()
        if not input_dir:
            self.throw_error('Please select a folder containing .tar.gz archives to decompress.')
            return
        self.run_backend_action(self.decompress_status_label,'Decompress',lambda api: api.decompress(input_dir))

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
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Run Custom Script",width =8,state=tk.DISABLED,command=self.copydata).place(relx=0.6,rely=0.91)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Register Custom Script to Overview",width =8,state=tk.DISABLED,command=self.copydata).place(relx=0.2,rely=0.91)

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
        image_path = os.path.join(self.wd, "BrainBeam/gui/images")
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


if __name__=='__main__':
    guioh=BrainBeamGuiBase()
    guioh()