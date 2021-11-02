"""
This file is a modified version of drf_plot.py
"""

import traceback
import sys
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

import digital_rf



def spectrum_process(
    data,
    sfreq,
    cfreq,
    toffset,
    modulus,
    integration,
    bins,
    log_scale,
    zscale,
    detrend,
    title,
    clr,
):
    """Break spectrum by modulus and display each block. Integration here acts
    as a pure average on the spectral data.
    """
    print("spectrum process!")

    if detrend:
        dfn = matplotlib.mlab.detrend_mean
    else:
        dfn = matplotlib.mlab.detrend_none

    win = np.blackman(bins)

    if modulus:
        block = 0
        block_size = integration * modulus
        block_toffset = toffset
        while block < len(data) / block_size:

            vblock = data[block * block_size : block * block_size + modulus]
            pblock, freq = matplotlib.mlab.psd(
                vblock,
                NFFT=bins,
                Fs=sfreq,
                detrend=dfn,
                window=win,
                scale_by_freq=False,
            )

            # complete integration
            for idx in range(1, integration):

                vblock = data[
                    block * block_size
                    + idx * modulus : block * block_size
                    + idx * modulus
                    + modulus
                ]
                pblock_n, freq = matplotlib.mlab.psd(
                    vblock,
                    NFFT=bins,
                    Fs=sfreq,
                    detrend=dfn,
                    window=matplotlib.mlab.window_hanning,
                    scale_by_freq=False,
                )
                pblock += pblock_n

            pblock /= integration

            # yield spectrum_plot(
            #     pblock, freq, cfreq, block_toffset, log_scale, zscale, title, clr
            # )

            block += 1
            block_toffset += block_size / sfreq

    else:
        pdata, freq = matplotlib.mlab.psd(
            data, NFFT=bins, Fs=sfreq, detrend=dfn, window=win, scale_by_freq=False
        )
        return pdata, freq
        # yield spectrum_plot(pdata, freq, cfreq, toffset, log_scale, zscale, title, clr)


def spectrum_plot(data, freq, cfreq, toffset, log_scale, zscale, title, clr):
    """Plot a spectrum from the data for a given fft bin size."""
    print("spectrum plot")
    tail_str = ""
    if log_scale:
        #        pss = 10.0*np.log10(data / np.max(data))
        pss = 10.0 * np.log10(data + 1e-12)
        tail_str = " (dB)"
    else:
        pss = data

    print(freq)
    freq_s = freq / 1.0e6 + cfreq / 1.0e6
    print(freq_s)
    zscale_low, zscale_high = zscale

    if zscale_low == 0 and zscale_high == 0:
        pss_ma = np.ma.masked_invalid(pss)
        if log_scale:
            zscale_low = np.median(pss_ma.min()) - 3.0
            zscale_high = np.median(pss_ma.max()) + 3.0
        else:
            zscale_low = np.median(pss_ma.min())
            zscale_high = np.median(pss_ma.max())

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(freq_s, pss, clr)
    print(freq_s[0], freq_s[-1], zscale_low, zscale_high)
    ax.axis([freq_s[0], freq_s[-1], zscale_low, zscale_high])
    ax.grid(True)
    ax.set_xlabel("frequency (MHz)")
    ax.set_ylabel("power spectral density" + tail_str, fontsize=12)
    ax.set_title(title)

    return fig



def read_digital_rf_data(input_files, plot_file=None, plot_type="spectrum", channel="",
		subchan=0, sfreq=0.0, cfreq=None, atime=0, start_sample=0, stop_sample=0, modulus=None, integration=1, 
		zscale=(0, 0), bins=256, log_scale=False, detrend=False,msl_code_length=0,
        msl_baud_length=0,save_plot = False, title="title"):

    for f in input_files:
        print(("file %s" % f))

        try:
            print("loading data")

            drf = digital_rf.DigitalRFReader(f)

            chans = drf.get_channels()
            if channel == "":
                chidx = 0
            else:
                chidx = chans.index(channel)

            print(f"chans: {chans}, chidx: {chidx}")
            ustart, ustop = drf.get_bounds(chans[chidx])
            print(f"ustart: {ustart}, ustop: {ustop}")

            print("loading metadata")

            drf_properties = drf.get_properties( chans[chidx])
            sfreq_ld       = drf_properties["samples_per_second"]
            sfreq          = float(sfreq_ld)
            toffset        = start_sample

            print(f"toffset: {toffset}")

            if atime == 0:
                atime = ustart
            else:
                atime = int(np.uint64(atime * sfreq_ld))

            sstart = atime + int(toffset)
            dlen   = stop_sample - start_sample

            print(f"sstart: {sstart}, dlen: {dlen}")

            if cfreq is None:
                # read center frequency from metadata
                metadata_samples = drf.read_metadata(
                    start_sample=sstart,
                    end_sample=sstart + dlen,
                    channel_name=chans[chidx],
                )
                # use center frequency of start of data, even if it changes
                for metadata in metadata_samples.values():
                    try:
                        cfreq = metadata["center_frequencies"].ravel()[subchan]
                    except KeyError:
                        continue
                    else:
                        break
                if cfreq is None:
                    print(
                        "Center frequency metadata does not exist for given"
                        " start sample."
                    )
                    cfreq = 0.0

            d = drf.read_vector(sstart, dlen, chans[chidx], subchan)


            print(f"d.shape: {d.shape}")

            print("d: ", d[0:10])

            if len(d) < (stop_sample - start_sample):
                print(
                    "Probable end of file, the data size is less than expected value."
                )
                sys.exit()

            if msl_code_length > 0:
                d = apply_msl_filter(d, msl_code_length, msl_baud_length)

           


        except:
            print(("problem loading file %s" % f))
            traceback.print_exc(file=sys.stdout)
            sys.exit()

    print(f"plot_type: {plot_type}")

    if plot_type == "spectrum":
        print('boop')
        # fig_gen = spectrum_process(
        p_data, freq = spectrum_process(
            d,
            sfreq,
            cfreq,
            toffset,
            modulus,
            integration,
            bins,
            log_scale,
            zscale,
            detrend,
            title,
            "b",
        )
        # print(f"fig_gen: {fig_gen}")
        return {'data': p_data, 'freq': freq, 'cfreq': cfreq}

    elif plot_type == "specgram":
        fig_gen = specgram_process(
            d,
            sfreq,
            cfreq,
            toffset,
            modulus,
            integration,
            bins,
            detrend,
            log_scale,
            zscale,
            title,
        )

    for fig in fig_gen:
        fig.tight_layout()
        if save_plot:
            print("saving plot")
            fig.savefig(plot_file, bbox_inches="tight", pad_inches=0.05)
        else:
            plt.show()

if __name__ == "__main__":
    # default values
    input_files     = []
    sfreq           = 0.0
    cfreq           = None
    plot_type       = None
    channel         = ""
    subchan         = 0  # sub channel to plot
    atime           = 0
    start_sample    = 0
    stop_sample     = 0
    modulus         = None
    integration     = 1

    zscale          = (0, 0)

    bins            = 256

    title           = ""
    log_scale       = False
    detrend         = False
    show_plots      = True
    plot_file       = ""

    msl_code_length = 0
    msl_baud_length = 0


    # imitate command
    # drf_plot.py -i "C:/Users/yanag/openradar/openradar_antennas_wb_hf/" -c discone:0 -r 0:1000000 -p specgram -b 1024 -l
    read_digital_rf_data(["C:/Users/yanag/openradar/openradar_antennas_wb_hf/"], plot_file=None, plot_type="spectrum", channel="discone",
		subchan=0, sfreq=0.0, cfreq=None, atime=0, start_sample=0, stop_sample=1000000, modulus=None, integration=1, 
		zscale=(0, 0), bins=1023, log_scale=True, detrend=False,msl_code_length=0,
        msl_baud_length=0)