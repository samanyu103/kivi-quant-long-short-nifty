import matplotlib.pyplot as plt

# Data from the table
time_minutes = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
pnl = [238539, 59593, 118137, 152127, 107094, 111153, 106238, 105713, 102545, 128704]

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(time_minutes, pnl, marker='o', linestyle='-', color='b', label="PNL vs Time")

# Add labels and title
plt.title("PNL vs Time (minutes)")
plt.xlabel("Time (minutes)")
plt.ylabel("PNL")
plt.grid(True)

# Add a legend
plt.legend()

# Save the plot as a PNG image
plt.savefig('pnl_vs_time.png')

# Show the plot
plt.show()
