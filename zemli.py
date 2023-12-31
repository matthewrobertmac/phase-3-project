import subprocess
from os import makedirs
from os.path import join
from google.cloud import storage
import time

class Photo:
    GCS_BUCKET = "raspberrypi4"
    GOOGLE_CLOUD_PROJECT = "pullupnyc"
    PHOTOS_DIR = "photos"
    PREFIX = "processed_"
    model = "ssd_mobilenet_v2_coco_quant_no_nms_edgetpu.tflite"
    labels = "coco_labels.txt"

    def __init__(self, photo_id, bucket_name, client_name=GOOGLE_CLOUD_PROJECT):
        self.photo_id = photo_id
        self.photo_path = f'photo_{photo_id}.jpg'
        self.bucket_name = bucket_name
        self.storage_client = storage.Client(client_name)
        self.bucket = self.storage_client.bucket(bucket_name)
        self.blob = None
        self.processed_photo_path = None
        self.added_labels = []

        makedirs(self.PHOTOS_DIR, exist_ok=True)

    def take(self):
        subprocess.run(['fswebcam', '-r', '1280x720', '--no-banner', self.photo_path])

    def process_image_with_google_coral_edge_tpu(self):
        cmd = [
            "python3",
            "small_object_detection.py",
            "--model", self.model,
            "--label", self.labels,
            "--input", join(self.photo_path),
            "--tile_size", "1352x900,700x700, 500x500, 250x250",
            "--tile_overlap", "50",
            "--score_threshold", "0.25",
            "--output", join(f"{self.PREFIX}{self.photo_path}")
        ]
        subprocess.run(cmd, check=True)
        self.processed_photo_path = join(f"{self.PREFIX}{self.photo_path}")

        new_blob = self.bucket.blob(join(self.PREFIX + self.blob.name))
        new_blob.upload_from_filename(self.processed_photo_path)

    def upload(self, destination_blob_prefix='photo'):
        self.blob = self.bucket.blob(f'{destination_blob_prefix}{self.photo_id}.jpg')
        self.blob.upload_from_filename(self.photo_path)
        self.blob.make_public()
        self.process_image_with_google_coral_edge_tpu()

        return self.blob.public_url

    @staticmethod
    def list_bucket_images(bucket_name):
        storage_client = storage.Client('pullupnyc')
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs()
        image_names = [blob.name for blob in blobs if blob.content_type.startswith('image/')]
        for name in image_names:
            print(name)
        return len(image_names)


def terminal_interface():
    while True:
        print("\nInference Mesh")
        print("Please choose an option from the list:")
        print("1: Take a Photo")
        print("2: Take a Photo Burst")
        print("3: Run Video Server")
        print("4: Exit")

        inp = input("Enter a number: ")
        if inp == '1':
            take_a_photo()
        elif inp == '2':
            take_photo_burst()
        elif inp == '3':
            subprocess.run(['python3', 'video_server.py'], check=True)
        elif inp == '4':
            print("Exiting Inference Mesh...")
            break
        else: 
            print("Invalid input. Please select a number from the options below.")

def take_a_photo():
    bucket_name = 'raspberrypi4'
    photo_counter = Photo.list_bucket_images(bucket_name)
    while True:
        if input("Press Enter to take a photo (or 'q' to quit): ").lower() == 'q':
           return terminal_interface('6')
        photo = Photo(photo_counter, bucket_name)
        photo.take()
        photo_url = photo.upload()
        photo_counter += 1
        if input("Continue taking photos? (y/n): ").lower() != 'y':
            terminal_interface('6')
            break

def take_photo_burst():
    bucket_name = 'raspberrypi4'
    photo_counter = Photo.list_bucket_images(bucket_name)
    while True:
        if input("Press Enter to take 10 photos (or 'q' to quit): ").lower() == 'q':
           return terminal_interface('6')
        for i in range(10):
            photo = Photo(photo_counter, bucket_name)
            photo.take()
            photo_url = photo.upload()
            photo_counter += 1
        if input("Continue taking photo bursts? (y/n): ").lower() != 'y':
            terminal_interface('6')
            break

def main():
    terminal_interface()

if __name__ == '__main__':
    main()

