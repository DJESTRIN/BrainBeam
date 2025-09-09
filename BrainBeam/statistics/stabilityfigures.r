library(ggplot2)
library(tidyr)
library(dplyr)
library(scales)  # make sure you have this loaded for label_math

# Load your data
df <- read.csv("C:\\Users\\listo\\communal_registration_logcal_drop\\rabies_experiment\\results\\dfsum.csv")

# Small epsilon added to avoid zero
epsilon <- 1e-6
df$normalizedcount <- df$normalizedcount + epsilon

# Calculate mean, SEM, and SD for each region
df_summary <- df %>%
  group_by(group, regionname, lateralization) %>%
  summarize(
    mean = mean(normalizedcount, na.rm = TRUE),
    sem = sd(normalizedcount, na.rm = TRUE) / sqrt(n()),
    sd = sd(normalizedcount, na.rm = TRUE),
    n = n(),
    .groups = 'drop'
  )

# Pivot wider
wide_df <- df_summary %>%
  pivot_wider(
    names_from = group,
    values_from = c(mean, sem, sd, n)
  )

# Calculate Cohen's d
wide_df <- wide_df %>%
  mutate(
    pooled_sd = sqrt(((n_control - 1) * sd_control^2 + (n_cort - 1) * sd_cort^2) / (n_control + n_cort - 2)),
    cohen_d = (mean_control - mean_cort) / pooled_sd
  )

# Compute error bars (mean ± SEM)
wide_df <- wide_df %>%
  mutate(
    control_ymax = mean_control + sem_control,   # Upper bound for control
    cort_ymax = mean_cort + sem_cort            # Upper bound for cort
  )

# Get the top 5 regions with the largest absolute Cohen's d
top_regions <- wide_df %>%
  arrange(desc(abs(cohen_d))) %>%
  slice(1:5) %>%
  pull(regionname)

# Create a sequence of x values across the range of your data
x_vals <- seq(min(wide_df$mean_control), max(wide_df$mean_control), length.out = 10000)

# Calculate y based on your model
y_vals <- 0.767 * x_vals + 0.00709
lower_ci <- 0.69519 * x_vals + 0.00709
upper_ci <- 0.8394 * x_vals + 0.00709

# Create data frame
df <- data.frame(
  group = factor(c("All Regions", "Regions with Weak Effects", "Regions with Strong Effects"),
                 levels = c("All Regions", "Regions with Weak Effects", "Regions with Strong Effects")),
  mean = c(0.767, 1.0012765843164158, 0.7473318508789027),
  lower = c(0.69519, 0.8878740264879387, 0.6403614398644412),
  upper = c(0.8394, 1.1146791421448927, 0.8543022618933643)
)


p <- ggplot(df, aes(x = group, y = mean)) +
  geom_hline(yintercept = 1, linetype = "dashed", color = "black", linewidth = 0.8) +
  geom_errorbar(aes(ymin = lower, ymax = upper), width = 0.1, linewidth = 1.5, color = "#8e7cc3") +
  geom_point(shape = 21, fill = "white", color = "#8e7cc3", size = 5, stroke = 3) +
  labs(x = NULL, y = "Slope") +
  theme_minimal(base_size = 14) +
  theme(
    axis.text.x = element_text(angle = 30, hjust = 1),
    axis.text = element_text(color = "black"),
    axis.ticks = element_line(color = "black", linewidth = 0.8),   # <-- add thick black ticks
    axis.ticks.length = unit(0.25, "cm"),                          # <-- make ticks longer
    axis.line = element_line(color = "black", linewidth = 0.8),    # <-- thicken axis lines
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    panel.border = element_blank()
  )

print(p)




# Make a data frame
regression_df <- data.frame(x = x_vals, y = y_vals, ymin = lower_ci, ymax = upper_ci)

p <- ggplot(wide_df, aes(x = mean_control, y = mean_cort, fill = cohen_d)) +
  geom_errorbar(aes(ymin = mean_cort, ymax = cort_ymax), width = 0, size = 1) +
  geom_errorbarh(aes(xmin = mean_control, xmax = control_ymax), height = 0, size = 1) +
  geom_point(size = 3, shape = 21, color = "black", stroke = 1) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "black", size=1) +
  
  # 1. Add confidence band
  geom_ribbon(data = regression_df, aes(x = x, ymin = ymin, ymax = ymax), inherit.aes = FALSE, fill = "#4CAF50", alpha = 0.3) +
  
  # 2. Add main green regression line
  geom_line(data = regression_df, aes(x = x, y = y), inherit.aes = FALSE, color = "#4CAF50", size = 1) +
  
  scale_x_log10(
    breaks = c(1e-6,1e-4,1e-2,1e0),
    labels = c("0", expression(10^{-4}), expression(10^{-2}),expression(10^{0}))
  ) +
  scale_y_log10(
    breaks = c(1e-6,1e-4,1e-2,1e0),
    labels = c("0", expression(10^{-4}), expression(10^{-2}),expression(10^{0}))
  ) +
  scale_fill_gradient2(midpoint = 0, low = "red", mid = "white", high = "blue") +
  theme_classic() +
  theme(
    axis.line = element_line(size = 1),
    axis.text = element_text(size = 14),
    axis.title = element_text(size = 16),
    axis.ticks.length = unit(0.3, "cm"),
    axis.ticks = element_line(size = 1)
  ) +
  labs(
    x = "Control (Normalized Cell Count)", 
    y = "CORT (Normalized Cell Count)", 
    fill = "Cohen's D"
  )

print(p)

wide_df$label<-paste(wide_df$regionname,wide_df$lateralization)
df$label<-paste(df$regionname,df$lateralization)
top30_regions <- wide_df %>%
  arrange(desc(abs(cohen_d))) %>%
  slice_head(n = 30) %>%
  pull(label)

# 2. Filter the original df to only those regions
df_top30 <- df %>%
  filter(label %in% top30_regions)

# 3. Summarize mean ± SEM for each group and region
df_summary_top30 <- df_top30 %>%
  group_by(group, label) %>%
  summarize(
    mean = mean(normalizedcount, na.rm = TRUE),
    sem = sd(normalizedcount, na.rm = TRUE) / sqrt(n()),
    .groups = 'drop'
  )

p <- ggplot(df_summary_top30, aes(x = group, y = mean, fill = group)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), width = 0.5) +
  geom_errorbar(aes(ymin = mean - sem, ymax = mean + sem),
                width = 0,
                position = position_dodge(width = 0.8),size=0.9) +
  scale_fill_manual(values = c("control" = "#00b3fb", "cort" = "#fd5f6d")) +
  labs(x="",y = "Normalized Cell Count", fill = "Group") +
  theme_classic() +
  theme(
    axis.text.y = element_text(size = 10),
    axis.title = element_text(size = 14),
    legend.title = element_text(size = 14),
    legend.text = element_text(size = 12),
    strip.text = element_text(size = 6),  # Adjust facet label size
    strip.background = element_blank(),  # Remove box around facets
    panel.grid.major = element_blank(),  # Remove major grid lines (if needed)
    panel.grid.minor = element_blank()   # Remove minor grid lines (if needed)
  ) +
  facet_wrap(~label, scales = "free_y", ncol = 5, labeller = label_wrap_gen(width = 20))  # Wrap labels

print(p)



# Load your data
weights <- read.csv("C:\\Users\\listo\\communal_registration_logcal_drop\\rabies_experiment\\results\\weightswide.csv")
weights_30 <- head(weights, 30)
weights_30$regionname <- factor(weights_30$regionname, levels = weights_30$regionname[order(weights_30$weights, decreasing = TRUE)])

# Plot the data with horizontal bars, regionname as labels, and a gradient fill
p <- ggplot(weights_30, aes(x = weights, y = regionname, color = weights)) +
  geom_segment(aes(x = 0, xend = weights, y = regionname, yend = regionname),
               size = 1.2) +  # The stick part
  geom_point(size = 4) +  # The lollipop head
  scale_color_gradient(low = "#1b7837", high = "#b7e4c7") +
  labs(x = "Slope Stability Weights", y = "") +
  theme_minimal() +
  theme(
    axis.text.x = element_text(size = 10),
    axis.text.y = element_text(size = 10),
    axis.title = element_text(size = 14),
    plot.title = element_text(size = 16)
  )

print(p)

df <- data.frame(
  category = c("PFC", "Non-PFC"),
  percent = c(63, 37)
)

p <- ggplot(df, aes(x = "", y = percent, fill = category)) +
  geom_col(width = 1, color = "black", size = 2) +  # Adjust the size for thicker outlines
  coord_polar(theta = "y") +
  scale_fill_manual(values = c("#b7e4c7", "#1b7837")) +  # Nice greens
  labs(title = "PFC vs Non-PFC Regions") +
  theme_void() +
  theme(
    plot.title = element_text(size = 16, hjust = 0.5),
    legend.title = element_blank(),
    plot.margin = margin(0, 0, 0, 0)  # Remove margins around the plot
  )
print(p)
