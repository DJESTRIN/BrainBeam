import napari
import numpy as np
import tifffile
import ipdb

file = r'C:\Users\listo\communal_registration_logcal_drop\control\cage4467199_animal2_registration\registration_drop\downsampled_moving_image.tiff'
image_data = tifffile.imread(file)

# crop data
image_data[112:148,0:71,:] = 0
image_data[148:170,0:165,:] = 0
image_data[170:183,0:200,:] = 0
image_data[179:,:,:] = 0
image_data[146:157,:130,213:] = 0
image_data[157:,:200,:] = 0

new_file = r'C:\Users\listo\communal_registration_logcal_drop\control\cage4467199_animal2_registration\registration_drop\downsampled_moving_image_manual_cropped.tiff'
tifffile.imwrite(new_file,image_data)
# print(image_data.shape)
# viewer = napari.view_image(image_data)
# napari.run()
