/* weight_process.c — pure filtering, 1:1 with the Python reference model. */
#include "weight_process.h"

#include <math.h>
#include <string.h>

static double median_of(const double *values, int n)
{
    double tmp[HYDRATION_MAX_RAW];
    int i, j;

    if (n <= 0) {
        return 0.0;
    }
    for (i = 0; i < n && i < HYDRATION_MAX_RAW; i++) {
        tmp[i] = values[i];
    }
    for (i = 1; i < n; i++) {
        double key = tmp[i];
        j = i - 1;
        while (j >= 0 && tmp[j] > key) {
            tmp[j + 1] = tmp[j];
            j--;
        }
        tmp[j + 1] = key;
    }
    if (n % 2 == 1) {
        return tmp[n / 2];
    }
    return 0.5 * (tmp[n / 2 - 1] + tmp[n / 2]);
}

/* deque.append(maxlen=n): drop the oldest when full. */
static void append_fixed(double *buf, int *len, int cap, double v)
{
    if (*len < cap) {
        buf[*len] = v;
        (*len)++;
    } else if (cap > 0) {
        memmove(buf, buf + 1, (size_t)(cap - 1) * sizeof(double));
        buf[cap - 1] = v;
    }
}

void weight_process_init(weight_process_t *wp, const hydration_config_t *cfg)
{
    memset(wp, 0, sizeof(*wp));
    wp->filter_n = cfg->filter_n;
    wp->stable_n = cfg->stable_n;
    wp->stable_range_g = cfg->stable_range_g;
    wp->spike_g = cfg->spike_g;
}

void weight_process_reset(weight_process_t *wp)
{
    wp->raw_len = 0;
    wp->filt_len = 0;
}

weight_sample_class_t weight_process_push(weight_process_t *wp, double raw_g, double *median_g)
{
    append_fixed(wp->raw, &wp->raw_len, wp->filter_n, raw_g);
    double m = median_of(wp->raw, wp->raw_len);
    append_fixed(wp->filt, &wp->filt_len, wp->stable_n, m);
    if (median_g != NULL) {
        *median_g = m;
    }

    if (fabs(raw_g - m) > wp->spike_g) {
        return WEIGHT_SAMPLE_SPIKE;
    }
    if (!weight_process_stable(wp)) {
        return WEIGHT_SAMPLE_UNSTABLE;
    }
    return WEIGHT_SAMPLE_STABLE;
}

bool weight_process_stable(const weight_process_t *wp)
{
    int i;
    double lo, hi;

    if (wp->filt_len < wp->stable_n) {
        return false;
    }
    lo = wp->filt[0];
    hi = wp->filt[0];
    for (i = 1; i < wp->filt_len; i++) {
        if (wp->filt[i] < lo) {
            lo = wp->filt[i];
        }
        if (wp->filt[i] > hi) {
            hi = wp->filt[i];
        }
    }
    return (hi - lo) <= wp->stable_range_g;
}

double weight_process_median(const weight_process_t *wp)
{
    return median_of(wp->raw, wp->raw_len);
}
