import os

remove_string = input("What characters would you like to remove from your file name?\n")
print("removing " + remove_string)

for file_name in os.listdir():
   if remove_string in file_name:
        new_file_name = file_name.replace(remove_string, "")
        os.rename(file_name, new_file_name)
        print("renaming " + file_name + " to " + new_file_name)