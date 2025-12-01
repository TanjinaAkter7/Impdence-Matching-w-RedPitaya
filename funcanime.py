import redpitaya_scpi as rp_scpi
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.image as mpimg

rp_host = 'rp-f0d4f7.local'
rp = rp_scpi.scpi(rp_host)

background_image_path = "g4RWTAER.png"
bg_img = mpimg.imread(background_image_path)

fig, ax = plt.subplots(figsize=(8, 8))
ax.imshow(bg_img, extent=[-1.2, 1.2, -1.2, 1.2], aspect='auto')
ax.set_xlim(-1.2, 1.2)
ax.set_ylim(-1.2, 1.2)
ax.set_aspect('equal')
ax.set_title("Smith Chart with Real-Time Data")
ax.set_xlabel("Real Part")
ax.set_ylabel("Imaginary Part")
point_plot, = ax.plot([], [], 'ro', label="Current Point")
ax.legend()

SIGNAL_CHANGE_THRESHOLD = 0.001
NUM_AVG = 5
last_magnitude = None

def smith_chart_coordinates(magnitude, phase):
    x = magnitude * np.cos(phase)
    y = magnitude * np.sin(phase)
    return x, y

def acquire_one_snapshot():
    rp.tx_txt("ACQ:RST")
    rp.tx_txt("ACQ:START")
    rp.tx_txt("ACQ:DEC 8")
    rp.tx_txt("ACQ:TRIG CH1_PE")
    rp.tx_txt("ACQ:TRIG:LEV 0.5")
    rp.tx_txt("ACQ:TRIG:DLY 8192")

    while True:
        rp.tx_txt("ACQ:TRIG:STAT?")
        if rp.rx_txt().strip() == "TD":
            break

    rp.tx_txt("ACQ:SOUR1:DATA?")
    ch1_str = rp.rx_txt().strip('{}\n\r').replace(" ", "").split(',')
    ch1_str.pop(0)
    ch1 = np.array(list(map(float, ch1_str)))

    rp.tx_txt("ACQ:SOUR2:DATA?")
    ch2_str = rp.rx_txt().strip('{}\n\r').replace(" ", "").split(',')
    ch2_str.pop(0)
    ch2 = np.array(list(map(float, ch2_str)))

    rp.tx_txt("ACQ:STOP")
    return ch1, ch2


def compute_phase_and_magnitude(ch1, ch2):

    
    # Remove DC
    ch1 = ch1 - np.mean(ch1)
    ch2 = ch2 - np.mean(ch2)

    amp1 = (max(ch1) - min(ch1)) / 2
    amp2 = (max(ch2) - min(ch2)) / 2

    # Calculate phase shift
    dot = np.dot(ch1, ch2)
    cross = np.dot(ch1, np.roll(ch2, +len(ch2)//4))  # 90 degree phase shift
    phase_rad = np.arctan2(cross, dot)

    magnitude = amp2 / amp1 if amp1 != 0 else 0

    return magnitude, phase_rad

# Get stable average by repeating measurement
def get_stable_avg():
    magnitudes = []
    phases = []

    for _ in range(NUM_AVG):
        ch1, ch2 = acquire_one_snapshot()
        mag, phase = compute_phase_and_magnitude(ch1, ch2)
        magnitudes.append(mag)
        phases.append(phase)
    
    return np.mean(magnitudes), np.mean(phases)

# Animation update
def update(frame):
    global last_magnitude

    mag, phase = get_stable_avg()

    # Skip if signal hasn't changed
    if last_magnitude is not None and abs(mag - last_magnitude) < SIGNAL_CHANGE_THRESHOLD:
        return
    
    last_magnitude = mag

    x, y = smith_chart_coordinates(mag, phase)
    ax.clear()
    ax.imshow(bg_img, extent=[-1.2, 1.2, -1.2, 1.2], aspect='auto')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.set_title("Smith Chart with Real-Time Data")
    ax.set_xlabel("Real Part")
    ax.set_ylabel("Imaginary Part")

    #If magnitude is too low, show center (Perfect Match)
    if mag < 0.05:
        ax.plot(0,0, 'ro', label="|Γ|≈ 0 (Matched)")
    else:
        x, y = smith_chart_coordinates (mag, phase)   
        ax.plot(x, y, 'ro', label=f"|Γ|={mag:.2f}, ∠={phase:.1f}")
    ax.legend()

# Animate every 0.1 seconds (enough time for 10 acquisitions)
ani = animation.FuncAnimation(fig, update, interval=100)
plt.show()
