import cv2
import os

input_folder = "bill_image"
output_folder = "image_cleaning_one_folder"

def image_cleaning(input_folder, output_folder):
    valide_extension = (".jpg", ".jpeg", ".png")
    converted_count = 0

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(valide_extension):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            try:
                color_image = cv2.imread(input_path)

                # Converting it into greyScale / black&white image
                grey_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

                # Removing the noise from the image
                blur_image = cv2.GaussianBlur(grey_image, (5,5), 0)

                # Otsu's Binarization
                ret, binary_image = cv2.threshold(blur_image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                cv2.imwrite(output_path, binary_image)

                converted_count += 1
                print(f"image_converted{converted_count}{filename}")
            except Exception as e:
                print(f"Failed to convert {filename}{e}")

if __name__ == "__main__":
    image_cleaning(input_folder, output_folder)