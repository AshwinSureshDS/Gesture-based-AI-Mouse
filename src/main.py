import cv2
import numpy as np
import threading
import time
import mouse
import pyautogui
import datetime

from utils.hand_detector import HandDetector
from utils.button import TextButton

def main():
    detector = HandDetector(detectionCon=0.9, maxHands=1)

    cap = cv2.VideoCapture(0)
    cam_width, cam_height = 640, 480
    cap.set(3, cam_width)
    cap.set(4, cam_height)

    frameR = 120  # Increased Frame Reduction for better edge handling

    # Mouse smoothing variables
    smoothening = 5
    prev_x, prev_y = 0, 0
    curr_x, curr_y = 0, 0

    # delay for the mouse to move
    l_delay = 0 
    r_delay = 0

    def l_clk_delay():
        nonlocal l_delay
        nonlocal l_clk_thread
        time.sleep(1) # delay for the mouse to move
        l_delay = 0
        l_clk_thread = threading.Thread(target=l_clk_delay)

    def r_clk_delay():
        nonlocal r_delay
        nonlocal r_clk_thread
        time.sleep(1) # delay for the mouse to move
        r_delay = 0
        r_clk_thread = threading.Thread(target=r_clk_delay)

    l_clk_thread = threading.Thread(target=l_clk_delay)

    r_clk_thread = threading.Thread(target=r_clk_delay)

    # screenshot delay
    s_delay = 0
    
    # Drag state
    dragging = False
    
    def s_clk_delay():
        nonlocal s_delay
        nonlocal s_clk_thread
        time.sleep(2) # 2 second delay for screenshots
        s_delay = 0
        s_clk_thread = threading.Thread(target=s_clk_delay)
        
    s_clk_thread = threading.Thread(target=s_clk_delay)

    # Create buttons
    buttons = [
        TextButton("Mouse Moving", 10, 5),
        TextButton("Mouse Lock", 200, 5),
        TextButton("Drag Mode", 390, 5),
        TextButton("Left Click", 10, 45),
        TextButton("Right Click", 200, 45),
        TextButton("Double Click", 390, 45),
        TextButton("Scroll Up", 10, 85),

        TextButton("Scroll Down", 200, 85),
        TextButton("Screenshot", 390, 85)
    ]

    def reset_buttons():
        for button in buttons:
            if button.active_until == 0:  # Only reset if not in timed active state
                button.is_active = False

    try:
        while True:
            success, img = cap.read()
            if not success:
                print("Failed to grab frame")
                break

            img = cv2.flip(img, 1)
            hands, img = detector.findHands(img, flipType=False)
            
            # Reset all buttons to default state
            reset_buttons()
            
            cv2.rectangle(img, (frameR, frameR), (cam_width - frameR, cam_height - frameR), (255, 0, 0), 2)

            if hands:
                lmlist = hands[0]["lmList"]
                ind_x, ind_y = lmlist[8][0], lmlist[8][1]
                mid_x, mid_y = lmlist[12][0], lmlist[12][1]

                cv2.circle(img, (ind_x, ind_y), 10, (0, 255, 0), cv2.FILLED)
                fingers = detector.fingersUp(hands[0])
                
                # Reset moving and lock buttons
                buttons[0].is_active = False
                buttons[1].is_active = False
                buttons[2].is_active = False # Drag Mode (Note: logic below uses index 2 which is WRONG based on insertion order)

                
                # Check for Drag (Pinch: Index + Thumb)
                thumb_x, thumb_y = lmlist[4][0], lmlist[4][1]
                drag_length, _, _ = detector.findDistance((thumb_x, thumb_y), (ind_x, ind_y), img)
                
                if drag_length < 40:
                    if not dragging:
                        # WARNING: If the mouse cursor is over the OpenCV window title bar or borders
                        # when this press happens, Windows may pause the application loop!
                        mouse.press(button='left')
                        dragging = True
                    buttons[2].is_active = True # Drag Mode
                else:
                    if dragging:
                        mouse.release(button='left')
                        dragging = False
                    buttons[2].is_active = False

                # Mouse Movement
                if ((fingers[1] == 1 and fingers[2] == 0 and fingers[0] == 1) or dragging):
                    buttons[0].is_active = True  # Mouse Moving
                    converted_x = np.interp(ind_x, [frameR, cam_width - frameR], [0, 1536])
                    converted_y = np.interp(ind_y, [frameR, cam_height - frameR], [0, 864])
                    
                    curr_x = prev_x + (converted_x - prev_x) / smoothening
                    curr_y = prev_y + (converted_y - prev_y) / smoothening
                    
                    curr_x = max(0, min(curr_x, 1536))
                    curr_y = max(0, min(curr_y, 864))
                    
                    mouse.move(int(curr_x), int(curr_y))
                    prev_x, prev_y = curr_x, curr_y
                elif fingers[1] == 1 and fingers[2] == 1 and fingers[0] == 1:
                    buttons[1].is_active = True  # Mouse Lock - instant state
                    
                # Mouse Click actions
                if fingers[1] == 1 and fingers[2] == 1 and fingers[0] == 1:
                    length, _, img = detector.findDistance((ind_x, ind_y), (mid_x, mid_y), img)
                    if length < 40:
                        if fingers[3] == 0 and fingers[4] == 0 and l_delay == 0:
                            buttons[3].set_active()  # Left Click
                            mouse.click(button='left')
                            l_delay = 1
                            l_clk_thread.start()
                        elif fingers[3] == 1 and fingers[4] == 0 and r_delay == 0:
                            buttons[4].set_active()  # Right Click
                            mouse.click(button='right')
                            r_delay = 1
                            r_clk_thread.start()
                        elif fingers[3] == 0 and fingers[4] == 1:
                            buttons[5].set_active()  # Double Click
                            mouse.double_click(button='left')
                            
                # Scroll actions
                if fingers[1] == 1 and fingers[2] == 1 and fingers[0] == 0:
                    length, _, img = detector.findDistance((ind_x, ind_y), (mid_x, mid_y), img)
                    if length < 30:
                        if fingers[4] == 1:
                            buttons[6].set_active()  # Scroll Up
                            mouse.wheel(delta=1)
                        else:
                            buttons[7].set_active()  # Scroll Down

                            mouse.wheel(delta=-1)

                # Screenshot Action (Shaka Gesture: Thumb + Pinky)
                if fingers[0] == 1 and fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 1:
                    if s_delay == 0:
                        buttons[8].set_active()
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshot_{timestamp}.png"
                        pyautogui.screenshot(filename)
                        print(f"Screenshot saved: {filename}")
                        s_delay = 1
                        s_clk_thread.start()
            
            # Draw all buttons
            for button in buttons:
                button.draw(img)

            cv2.imshow("AI Mouse - Camera Feed", img)
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q') or key & 0xFF == 27:
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()