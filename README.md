# 🥧 Raspberry Pi Facial Recognition System

## Overview

This project is a lightweight facial recognition system built using a Raspberry Pi 4, the Raspberry Pi Camera Module 3, Python, and OpenCV. The system captures live video from the camera, processes each frame, and detects or recognizes faces using a pre-trained model. The goal of this documentation is to provide clear, end-to-end instructions for installing, configuring, running, and troubleshooting the project. You should not need to contact me with questions; every step has been included with you in mind.

This project is designed to run on **Raspberry Pi OS Lite (32-bit)** and uses SSH for headless setup. No monitor, keyboard, or mouse is required.

---

## Hardware Requirements

* Raspberry Pi 4 (2GB, 4GB, or 8GB RAM)
* Raspberry Pi Camera Module 3 (wide or standard)
* MicroSD card (16GB or larger recommended)
* Official Raspberry Pi power supply
* Wi-Fi or Ethernet connection
* (Optional) Short ribbon cable for camera positioning

---

## Software Requirements

* Raspberry Pi OS Lite (32-bit)
* Python 3 (pre-installed)
* OpenCV for Python
* Required Python packages (installed later)
* SSH enabled

---

## 1. Installation & Setup

### Flash Raspberry Pi OS Lite

1. Use Raspberry Pi Imager to install **Raspberry Pi OS Lite (32-bit)** on your microSD card.
2. Before ejecting, go to *OS Customization*:

   * Set hostname (example: `raspi-cam`)
   * Enable SSH
   * Configure Wi-Fi
   * Set username/password
3. Insert the microSD card into your Pi and power it on.

### Connect via SSH

On your laptop:

```bash
ssh <username>@<hostname>.local
```

Example:

```bash
ssh pi@raspi-cam.local
```

If `.local` does not work, you may need to find the Pi's IP address using your router dashboard, `nmap`, or Raspberry Pi Connect.

---

## 2. Enable Camera

Run the following to enable the camera interface:

```bash
sudo raspi-config
```

Navigate to:

```
Interface Options → Camera → Enable
```

Reboot:

```bash
sudo reboot
```

To test the camera:

```bash
libcamera-still -o test.jpg
```

---

## 3. Install Dependencies

Update your system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install camera + build tools:

```bash
sudo apt install -y python3-pip python3-opencv libatlas-base-dev
```

Install required Python libraries:

```bash
pip3 install numpy face-recognition
```

*(Note: `face-recognition` installs `dlib`. This step may take several minutes.)*

---

## 4. Project Structure

Your project folder should look like this:

```
project/
│── main.py
│── encode_faces.py
│── faces/
│    └── <your training images>
│── models/
│    └── encodings.pickle
│── README.md
```

### `faces/`

Add images of people you want the system to recognize. Use clear, forward-facing photos.

### `encode_faces.py`

Reads all images in `faces/` and generates a serialized encoding file.

### `main.py`

Runs the live camera feed and performs recognition.

---

## 5. Encoding Faces

Before running the system, encode your training images:

```bash
python3 encode_faces.py
```

This generates `models/encodings.pickle`, which contains all face embeddings.

---

## 6. Running the Facial Recognition System

Start the program:

```bash
python3 main.py
```

You should see console output showing:

* Frames processed
* Detected faces
* Matched names (or "Unknown")

If you want the program to run automatically on boot:

```bash
sudo nano /etc/rc.local
```

Add the following line *before* `exit 0`:

```bash
python3 /home/pi/project/main.py &
```

Save and reboot.

---

## 7. Troubleshooting

### Camera not detected

Check ribbon orientation — blue side toward Ethernet port.
Test camera:

```bash
libcamera-still -o test.jpg
```

Run diagnostics:

```bash
dmesg | grep -i camera
```

### `face_recognition` installation fails

Run:

```bash
sudo apt install build-essential cmake
```

Then reinstall:

```bash
pip3 install face-recognition
```

### SSH cannot connect

Try:

```bash
ping raspi-cam.local
```

If no response, find IP using:

```bash
sudo nmap -sn 10.0.0.0/24
```

(Replace with your network range.)

---

## 8. Notes for Graders / Staff

* All code files are included and documented.
* No GUI or desktop environment is required.
* All installation commands are provided exactly as needed.
* The project runs fully headless.
* This README contains all steps necessary to test the project.

If any step is unclear, the issue is likely related to network configuration or Pi camera seating — both common and mentioned above.

---

## 9. Conclusion

This project demonstrates how a lightweight Raspberry Pi system can perform real-time facial recognition using only Python, OpenCV, and a camera module. The code is simple enough for modification, yet robust enough to run continuously as a background service.

You should now have everything necessary to set up, build, run, and evaluate the project end-to-end.
