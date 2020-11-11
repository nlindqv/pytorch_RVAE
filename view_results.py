import argparse
import matplotlib
import matplotlib.pyplot as plt
import pylab
# %matplotlib inline

import numpy as np

if __name__=="__main__":
    matplotlib.rcParams['backend'] = 'TkAgg'
    print(matplotlib.rcParams['backend'])
    parser = argparse.ArgumentParser(description='Paraphraser')
    parser.add_argument('-m', '--model-name', default='', metavar='MN',
                        help='name of model to save (default: "")')

    parser.add_argument('-tpl', '--use_two_path_loss', default=False, type=bool, metavar='2PL',
                    help='use two path loss while training (default: False)')
    parser.add_argument('--gan', default=True, type=bool, metavar='GAN', help='GAN')
    parser.register('type', 'bool', lambda v: v.lower() in ["true", "t", "1"])
    args = parser.parse_args()



    #paraphraser.load_state_dict(t.load('saved_models/trained_paraphraser_' + args.model_name))

    ce_result_valid = list(np.load('logs/ce_result_valid_{}.npy'.format(args.model_name)))
    kld_result_valid = list(np.load('logs/kld_result_valid_{}.npy'.format(args.model_name)))
    ce_result_train = list(np.load('logs/ce_result_train_{}.npy'.format(args.model_name)))
    kld_result_train = list(np.load('logs/kld_result_train_{}.npy'.format(args.model_name)))
    if args.use_two_path_loss:
        ce2_result_valid = list(np.load('logs/ce2_result_valid_{}.npy'.format(args.model_name)))
        ce2_result_train = list(np.load('logs/ce2_result_train_{}.npy'.format(args.model_name)))
    if args.gan:
        ce2_result_valid = list(np.load('logs/ce2_result_valid_{}.npy'.format(args.model_name)))
        ce2_result_train = list(np.load('logs/ce2_result_train_{}.npy'.format(args.model_name)))
        dg_result_valid = list(np.load('logs/dg_result_valid_{}.npy'.format(args.model_name)))
        dg_result_train = list(np.load('logs/dg_result_train_{}.npy'.format(args.model_name)))
        d_result_valid = list(np.load('logs/d_result_valid_{}.npy'.format(args.model_name)))
        d_result_train = list(np.load('logs/d_result_train_{}.npy'.format(args.model_name)))
    # print(ce_result_valid)
    # print(np.arange(len(ce_result_valid)))

    iter = np.arange(len(ce_result_valid)) * 500
    plt.plot(iter, ce_result_train, iter, ce_result_valid)
    plt.legend(['Train', 'Validation'])
    plt.ylabel('Cross entropy loss')
    plt.savefig('results/ce_{}.png'.format(args.model_name))
    plt.clf()

    plt.plot(iter, kld_result_train, iter, kld_result_valid)
    plt.legend(['Train', 'Validation'])
    plt.ylabel('KL-divergence loss')
    plt.savefig('results/kld_{}.png'.format(args.model_name))
    plt.clf()

    train_loss = np.sum(np.stack([ce_result_train, kld_result_train, ce2_result_train], axis=0), axis=0)
    valid_loss = np.sum(np.stack([ce_result_valid, kld_result_valid, ce2_result_valid], axis=0), axis=0)
    plt.plot(iter, train_loss, iter, valid_loss)
    plt.legend(['Train', 'Validation'])
    plt.ylabel('Total loss')
    plt.savefig('results/total_{}.png'.format(args.model_name))
    plt.clf()
    # if args.gan:
    #     plt.plot(iter, ce_result_train+ce2_result_train+kld_result_train+dg_result_train, iter, ce_result_valid+ce2_result_valid+kld_result_valid+dg_result_valid)
    #     plt.legend(['Train', 'Validation'])
    #     plt.ylabel('Total loss')
    #     plt.savefig('results/total_{}.png'.format(args.model_name))

    x = np.load('logs/intermediate/sampled_out_20k_quora_testori_100k.txt.npy')
    print(x.shape)
