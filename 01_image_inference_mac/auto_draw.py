import cv2
import os

print("1. Python script started")

# File existence check
if not os.path.exists('bus.jpg'):
    print("Error: 'bus.jpg' not found.")
    exit()
if not os.path.exists('detections.txt'):
    print("Error: 'detections.txt' not found.")
    exit()

print("2. Loading image...")
img = cv2.imread('bus.jpg')
if img is None:
    print("Error: Could not read the image.")
    exit()

print("3. Reading detection coordinates...")
with open('detections.txt', 'r') as f:
    lines = f.readlines()

print(f"4. Starting drawing process (Total objects: {len(lines)})")
for line in lines:
    data = line.strip().split()
    if len(data) < 6: continue

    label, x1, y1, x2, y2, score = data[0], int(data[1]), int(data[2]), int(data[3]), int(data[4]), float(data[5])

    # Draw bounding box
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    # Add label text (Optional but recommended)
    cv2.putText(img, f"{label} {score:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    print(f"   - Drawn {label}: ({x1}, {y1}) at score {score}")

print("5. Saving the result...")
cv2.imwrite('result.jpg', img)

if os.path.exists('result.jpg'):
    print("Success: 'result.jpg' has been created!")
else:
    print("Error: Failed to save the file.")

# Attempting to display the window (Mac/Desktop environment)
try:
    print("6. Displaying image (Press any key to close)")
    cv2.imshow('Luckfox Detection Result', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
except Exception as e:
    print(f"Info: Could not display window (Reason: {e})")
