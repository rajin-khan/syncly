import os
import re
from Service import Service
from Dropbox import DropboxService
from GoogleDrive import GoogleDrive

#Manages multiple cloud storage services dynamically.
class DriveManager:
    def __init__(self, token_dir="tokens"):
        self.drives = []
        self.token_dir = token_dir
        self.sorted_buckets = []  # Initialize sorted_buckets as an empty list
        os.makedirs(self.token_dir, exist_ok=True)

    def add_drive(self, drive: Service, bucket_number):
        """
        Adds a storage service dynamically.
        """
        # Authenticate the drive
        drive.authenticate(bucket_number)

        self.drives.append(drive)
        print(f"{type(drive).__name__} added successfully as bucket {bucket_number}.")



    def check_all_storages(self):
        """
        Checks storage usage for all drives and sorts them by free space.
        :return: A tuple containing storage info, total limit, and total usage.
        """
        self.sorted_buckets = []  # Reset the sorted_buckets list
        storage_info = []
        total_limit = 0
        total_usage = 0
        for index, drive in enumerate(self.drives):
            limit, usage = drive.check_storage()
            free = limit - usage
            if free > 0 :  
                self.sorted_buckets.append((free, drive, index))  # Append (free_space, drive) for each Dropbox drive
                
            total_limit += limit
            total_usage += usage
            storage_info.append({
                "Drive Number": index + 1,
                "Storage Limit (bytes)": limit / 1024**3,
                "Used Storage (bytes)": usage / 1024**3,
                "Free Storage": (limit - usage) / 1024**3,
                "Provider": type(drive).__name__
            })

        # Sort buckets by free space in descending order
        self.sorted_buckets.sort(reverse=True, key=lambda x: x[0])
        return storage_info, total_limit, total_usage

    def get_sorted_buckets(self):
        """
        Returns the sorted list of buckets with the most free space.
        """
        return self.sorted_buckets

    def update_sorted_buckets(self):
        """
        Updates the sorted list of buckets based on current storage status.
        """
        self.check_all_storages()

    def get_all_authenticated_buckets(self):
        """
        Retrieves all authenticated bucket numbers from stored tokens.
        """
        return [
            f.replace(".json", "").replace("bucket_", "")
            for f in os.listdir(self.token_dir)
            if f.startswith("bucket_") and f.endswith(".json")
        ]

    @staticmethod
    def parse_part_info(file_name):
        #Extract base name and part number from split filenames with improved regex.
        patterns = [
            r'^(.*?)\.part(\d+)$',                 # .part0, .part1
            r'^(.*?)_part[\_\-]?(\d+)(\..*)?$',    # _part0, _part_1, _part-2
            r'^(.*?)\.(\d+)$',                     # .000, .001 (common split convention)
            r'^(.*?)(\d{3})(\..*)?$'               # Generic 3-digit numbering (e.g., .001)
        ]

        for pattern in patterns:
            match = re.match(pattern, file_name)
            if match:
                base = match.group(1)
                part_num = match.group(2)
                #Handle different pattern groups
                if pattern == patterns[1] and match.group(3):
                    base += match.group(3) if match.group(3) else ''
                elif pattern == patterns[3] and match.group(3):
                    base += match.group(3)
                try:
                    return base, int(part_num)
                except ValueError:
                    continue
        return None, None

    #List files from all authenticated buckets, with optional search query.
    def list_files_from_all_buckets(self, query=None):
        """
        List files from all authenticated cloud services.
        :param query: Optional search query.
        """
        if not self.drives:
            print("No authenticated drives found. Please add a new bucket first.")
            return

        all_files = []
        seen_files = set()

        for drive in self.drives:
            try:
                files = drive.listFiles(query=query)
                for file in files:
                    file_name = file.get("name", "Unknown")
                    file_size = file.get("size", "Unknown")
                    file_path = file.get("path", "N/A")
                    provider = type(drive).__name__

                    if file_name not in seen_files:
                        all_files.append((file_name, provider, file_size, file_path))
                        seen_files.add(file_name)

            except Exception as e:
                print(f"Error retrieving files from {type(drive).__name__}: {e}")

        # Sort and display results
        all_files.sort(key=lambda x: x[0])  # Sort by file name

        #Pagination
        page_size = 30
        total_files = len(all_files)
        start_index = 0

        while start_index < total_files:
            #Display paginated file results
            print("\nFiles (Sorted Alphabetically):\n")
            for idx, (name, mime_type, size, file_url) in enumerate(all_files[start_index:start_index + page_size], start=start_index + 1):
                size_str = f"{float(size) / 1024 ** 2:.2f} MB" if size != 'Unknown' else "Unknown size"
                print(f"{idx}. {name} ({mime_type}) - {size_str}")
                print(f"   Press here to view file: {file_url}\n")      #Display clickable link

            start_index += page_size        #Move to next batch of files

            if start_index < total_files:
                more = input("\nDo you want to see more files? (y/n): ").strip().lower()
                if more != 'y':
                    break