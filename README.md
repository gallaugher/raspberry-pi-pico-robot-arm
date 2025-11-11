3D printed robot arm.
3D print is from:
https://www.printables.com/model/97370-easy-robot-arm-sg90-servos-now-steppers-too-update/comments#preview.UKbhm
You can add more servos, but I only use 3 - one for tilting what I call the base
I did not add servos to swivel the base or swivel the claw, but you can add those, and add another 3D printed part so you have a "two elbow" servo. I opted not to do add these extras to keep costs and complexity down for a nice class project that all can complete.

Parts I printed are in this file:

Instead of using the printed axels, I opted for 1/8" dowel, which can be snipped off with wire cutters. I hot-glued the dowels into place & I think this is a better solution.

PARTS:
- Raspbery Pi Pico (I used a 2W but any Pico should work) - https://www.adafruit.com/product/6315
- Two mini breadboards. You could always use one big one, but I use Monk Makes boards for my class since they have pico pin labels on the board, which really helps when working with the pico - https://www.adafruit.com/product/5422
- Three Micro Servo - High Powered, High Torque Metal Gear - TowerPro MG92B - https://www.adafruit.com/product/2307
  While you could use hte cheaper nylon gear  TowerPro SG92R I found they weren't really strong enough for a good build. The more expensiv servos are really worth it, if you can afford it. I was a classroom splurge to buy enough for all of my students.
- Joystick - I bought a bunch of these super-cheap ones off AliExpress, although I found the x and y values printed on the stick are opposite when one actually places these pins in the breadboard. So in my code you'll see what's labeled as X-axis as actually controlling the vertical axis, and vice-versa. - https://www.aliexpress.us/item/3256806299955871.html Joysticks are standard. They behalve like two potentiometers, so any stnadard joystick should work.
- A single momentary push button - Any standard button will work. I buy a bunch like this for my students - https://a.co/d/fdZCdJZ Note: Most joysticks include a wire for a button, that registeres when the joystick is tapped, but I found this was awkward on joysticks vertically mounted on the breadboard, so I had students use a separate button. If you laser-cut a wooden case & mounted the joystick, you could likely use the built-in button instead.
- At least 15 pin-pin breadboard wires. - a pack like this is fine - https://www.adafruit.com/product/1957
- A microUSB cable that supports data transfer, NOT a power-only cable.

WIRING DIAGRAM:
<img width="1286" height="723" alt="wiring diagram" src="https://github.com/user-attachments/assets/8873f7c0-ad4a-401c-952b-0784deae573e" />


