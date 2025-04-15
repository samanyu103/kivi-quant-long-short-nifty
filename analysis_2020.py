import matplotlib.pyplot as plt

# Time (minutes) and PNL data
time = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
pnl = [24881, -11588, 55658, 46748, 10761, 31523, 61412, 51700, 48648, 52392]

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(time, pnl, marker='o', linestyle='-', color='royalblue', linewidth=2)
plt.title("PNL vs Time", fontsize=16)
plt.xlabel("Time (minutes)", fontsize=14)
plt.ylabel("PNL", fontsize=14)
plt.grid(True)
plt.axhline(0, color='gray', linestyle='--', linewidth=1)
plt.tight_layout()

# Save the plot
plt.savefig("pnl_vs_time.png", dpi=300)
plt.show()
