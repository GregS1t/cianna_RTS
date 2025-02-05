#!/usr/bin/env python3
import argparse
import os
import sys
from astropy.io import fits

def verify_fits(file_path, min_size=1024):
    """
    Checks the validity of a FITS file.

    Args:
        file_path (str): Path to the FITS file.
        min_size (int): Minimum file size in bytes to consider the file valid.

    Returns:
        bool: True if the file is valid, False otherwise.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        print("File does not exist:", file_path)
        return False

    # Check the size of the file
    file_size = os.stat(file_path).st_size
    print("File size:", file_size, "bytes")
    if file_size < min_size:
        print("File is too small to be valid.")
        return False

    # Try to open the file using astropy
    try:
        hdul = fits.open(file_path)
        print("FITS file opened successfully.")

        # Print the header of the first HDU (Header/Data Unit)
        print("Header of the first HDU:")
        print(hdul[0].header)

        # Optionally, print the complete structure of the FITS file
        print("\nFITS file structure:")
        hdul.info()

        # Close the file to free up resources
        hdul.close()
        return True

    except Exception as e:
        print("Error while opening the FITS file:", e)
        return False


if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Verify a FITS file.')
    # Add a positional argument for the FITS file path
    parser.add_argument('fits_file', help='Path to the FITS file to be tested.')
    args = parser.parse_args()

    # Retrieve the FITS file path from the command-line arguments
    file_path = args.fits_file

    # Verify the FITS file
    valid = verify_fits(file_path)
    if valid:
        print("FITS file is valid.")
        sys.exit(0)
    else:
        print("FITS file is not valid.")
        sys.exit(1)
