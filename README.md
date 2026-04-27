# CCTV Surveillance & Intruder Detection System 🎥

An AI-powered surveillance system that performs automated attendance marking using face recognition and detects unauthorized individuals (intruders) in real time.

## Overview
This system allows users to register their faces into a database and automatically marks attendance when a recorded video is processed. If an unknown (unregistered) face is detected, the system identifies it as an intruder, triggers an alert sound, and logs the intruder’s image in a dedicated dashboard.

## Key Features
- 👤 User registration with face data storage
- 🎯 Face recognition-based attendance system
- 📹 Video input processing (pre-recorded video support)
- 🚨 Intruder detection for unknown faces
- 🔊 Alert system (beep sound on detection)
- 🖼️ Intruder dashboard to view detected faces
- 🧠 Real-time face comparison using computer vision

## Tech Stack
- **Programming Language:** Python  
- **Libraries:** OpenCV, NumPy  
- **Concepts Used:** Face Recognition, Computer Vision, Image Processing  

## System Workflow
1. User registers their face into the system.
2. A recorded video is provided as input.
3. The system scans faces frame-by-frame.
4. If a face matches the database → marked as **Present**.
5. If a face is unknown → classified as **Intruder**:
   - Alert sound is triggered  
   - Face image is captured and stored  
6. Intruder images are displayed in the dashboard.

## Project Structure
- Face registration module  
- Video processing & recognition module  
- Attendance marking system  
- Intruder detection & alert module  
- Dashboard for intruder monitoring  

## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/Bhavanish-Mantri/CCTV_surveillance_system.git
cd CCTV_surveillance_system
```
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Run the system:
```
python main.py
```
## Use Cases
- Smart attendance systems (colleges, offices)  
- Hostel and home security monitoring  
- AI-based surveillance applications  

## Future Enhancements
- Live camera feed integration (real-time processing)  
- Email/SMS alert notification system  
- Cloud-based database for scalability  
- Advanced dashboard with analytics and reporting  

## Author
**Bhavanish Mantri**  
- GitHub: https://github.com/Bhavanish-Mantri  
- LinkedIn: https://www.linkedin.com/in/bhavanish-mantri  
