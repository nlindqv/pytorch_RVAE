# -*- coding: utf-8 -*-
import argparse
import os
import sys

import numpy as np
import torch as t
from torch.optim import Adam
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable

import sample
from utils.batch_loader import BatchLoader
from model.parametersGAN import Parameters
from model.generator import Generator

def trainer(generator, optimizer, batch_loader):
    def train(i, batch_size, use_cuda, dropout):
        input = batch_loader.next_batch(batch_size, 'train')
        input = [var.cuda() if use_cuda else var for var in input]

        [encoder_input_source,
         encoder_input_target,
         decoder_input_source,
         decoder_input_target, target] = input

        (logits, logits2), _, kld = generator(dropout,
                (encoder_input_source, encoder_input_target),
                (decoder_input_source, decoder_input_target),
                z=None, use_cuda=use_cuda)

        target = target.view(-1)
        cross_entropy, cross_entropy2 = [], []

        logits = logits.view(-1, generator.params.vocab_size)
        cross_entropy = F.cross_entropy(logits, target)

        logits2 = logits2.view(-1, generator.params.vocab_size)
        cross_entropy2 = F.cross_entropy(logits2, target)

        loss = generator.params.cross_entropy_penalty_weight * (cross_entropy + cross_entropy2) \
             + generator.params.get_kld_coef(i) * kld

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        return (cross_entropy, cross_entropy2), kld, generator.params.get_kld_coef(i)

    return train


if __name__ == "__main__":
    print(sys.getdefaultencoding())
    print(sys.getfilesystemencoding())
    parser = argparse.ArgumentParser(description='Paraphraser')
    parser.add_argument('--num-iterations', type=int, default=300000, metavar='NI',
                        help='num iterations (default: 60000)')
    parser.add_argument('--batch-size', type=int, default=32, metavar='BS',
                        help='batch size (default: 32)')
    parser.add_argument('-cuda', '--use-cuda', type=bool, default=True, metavar='CUDA',
                        help='use cuda (default: True)')
    parser.add_argument('--learning-rate', type=float, default=0.00005, metavar='LR',
                        help='learning rate (default: 0.00005)')
    parser.add_argument('--dropout', type=float, default=0.3, metavar='DR',
                        help='dropout (default: 0.3)')
    parser.add_argument('-ut', '--use-trained', type=bool, default=False, metavar='UT',
                        help='load pretrained model (default: False)')
    parser.add_argument('-m', '--model-name', default='', metavar='MN',
                        help='name of model to save (default: "")')
    parser.add_argument('--weight-decay', default=0.0, type=float, metavar='WD',
                        help='L2 regularization penalty (default: 0.0)')
    parser.add_argument('--use-quora', default=False, type=bool, metavar='quora',
                    help='if include quora dataset (default: False)')
    parser.add_argument('--interm-sampling', default=True, type=bool, metavar='IS',
                    help='if sample while training (default: False)')
    parser.add_argument('-tpl', '--use_two_path_loss', default=False, type=bool, metavar='2PL',
                    help='use two path loss while training (default: False)')
    parser.register('type', 'bool', lambda v: v.lower() in ["true", "t", "1"])
    args = parser.parse_args()

    batch_loader = BatchLoader()
    parameters = Parameters(batch_loader.max_seq_len,
                            batch_loader.vocab_size)

    generator = Generator(parameters)
    ce_result_valid = []
    kld_result_valid = []
    ce_result_train = []
    kld_result_train = []
    ce_cur_train = []
    kld_cur_train = []
    if args.use_two_path_loss:
        ce2_cur_train = []
        ce2_result_train = []
        ce2_result_valid = []

    if args.use_trained:
        paraphraser.load_state_dict(t.load('saved_models/trained_paraphraser_' + args.model_name))
        ce_result_valid = list(np.load('logs/ce_result_valid_{}.npy'.format(args.model_name)))
        kld_result_valid = list(np.load('logs/kld_result_valid_{}.npy'.format(args.model_name)))
        ce_result_train = list(np.load('logs/ce_result_train_{}.npy'.format(args.model_name)))
        kld_result_train = list(np.load('logs/kld_result_train_{}.npy'.format(args.model_name)))
        if args.use_two_path_loss:
            ce2_result_valid = list(np.load('logs/ce2_result_valid_{}.npy'.format(args.model_name)))
            ce2_result_train = list(np.load('logs/ce2_result_train_{}.npy'.format(args.model_name)))


    if args.use_cuda:
        paraphraser = paraphraser.cuda()

    optimizer = Adam(paraphraser.learnable_parameters(), args.learning_rate,
        weight_decay=args.weight_decay)

    train_step = trainer(paraphraser, optimizer, batch_loader)
    validate = paraphraser.validater(batch_loader)

    for iteration in range(args.num_iterations):

        (cross_entropy, cross_entropy2), kld, coef = train_step(iteration, args.batch_size, args.use_cuda, args.dropout)

        ce_cur_train += [cross_entropy.data.cpu().numpy()]
        kld_cur_train += [kld.data.cpu().numpy()]
        if args.use_two_path_loss:
            ce2_cur_train += [cross_entropy2.data.cpu().numpy()]

        # validation
        if iteration % 500 == 0:
            ce_result_train += [np.mean(ce_cur_train)]
            kld_result_train += [np.mean(kld_cur_train)]
            ce_cur_train, kld_cur_train = [], []

            if args.use_two_path_loss:
                ce2_result_train += [np.mean(ce2_cur_train)]
                ce2_cur_train = []

            print('\n')
            print('------------TRAIN-------------')
            print('----------ITERATION-----------')
            print(iteration)
            print('--------CROSS-ENTROPY---------')
            print(ce_result_train[-1])
            if args.use_two_path_loss:
                print('----CROSS-ENTROPY-2ND PATH----')
                print(ce2_result_train[-1])
            print('-------------KLD--------------')
            print(kld_result_train[-1])
            print('-----------KLD-coef-----------')
            print(coef)
            print('------------------------------')


            # averaging across several batches
            cross_entropy, cross_entropy2, kld = [], [], []
            for i in range(20):
                (ce, ce2), kl, _ = validate(args.batch_size, args.use_cuda)
                cross_entropy += [ce.data.cpu().numpy()]
                kld += [kl.data.cpu().numpy()]

                if args.use_two_path_loss:
                    cross_entropy2 += [ce2.data.cpu().numpy()]


            kld = np.mean(kld)
            cross_entropy = np.mean(cross_entropy)
            ce_result_valid += [cross_entropy]
            kld_result_valid += [kld]
            if args.use_two_path_loss:
                cross_entropy2 = np.mean(cross_entropy2)
                ce2_result_valid += [cross_entropy2]

            print('\n')
            print('------------VALID-------------')
            print('--------CROSS-ENTROPY---------')
            print(cross_entropy)
            if args.use_two_path_loss:
                print('----CROSS-ENTROPY-2ND-PATH----')
                print(cross_entropy2)
            print('-------------KLD--------------')
            print(kld)
            print('------------------------------')

            _, _, (sampled, s1, s2) = validate(2, args.use_cuda, need_samples=True)

            for i in range(len(sampled)):
                result = paraphraser.sample_with_pair(batch_loader, 20, args.use_cuda, s1[i], s2[i])

                print('source: ' + s1[i])
                print('target: ' + s2[i])
                print('valid: ' + sampled[i])
                print('sampled: ' + result)
                if args.use_two_path_loss:
                    result2 = paraphraser.sample_with_pair(batch_loader, 20, args.use_cuda, s1[i], s2[i], input_only=True)
                    print('sampled 2: ' + result2)
                print('...........................')

        # save model
        if (iteration % 10000 == 0 and iteration != 0) or iteration == (args.num_iterations - 1):
            t.save(paraphraser.state_dict(), 'saved_models/trained_paraphraser_' + args.model_name)
            np.save('logs/ce_result_valid_{}.npy'.format(args.model_name), np.array(ce_result_valid))
            np.save('logs/ce_result_valid_{}.npy'.format(args.model_name), np.array(ce_result_valid))
            np.save('logs/kld_result_valid_{}'.format(args.model_name), np.array(kld_result_valid))
            np.save('logs/ce_result_train_{}.npy'.format(args.model_name), np.array(ce_result_train))
            np.save('logs/kld_result_train_{}'.format(args.model_name), np.array(kld_result_train))
            if args.use_two_path_loss:
                np.save('logs/ce2_result_valid_{}.npy'.format(args.model_name), np.array(ce2_result_valid))
                np.save('logs/ce2_result_train_{}.npy'.format(args.model_name), np.array(ce2_result_train))


        #interm sampling
        if (iteration % 20000 == 0 and iteration != 0) or iteration == (args.num_iterations - 1):
            if args.interm_sampling:
                sample_file = 'quora_test'
                args.use_mean = False
                args.seq_len = 30

                (result, result2), target, source = sample.sample_with_input_file(batch_loader,
                                paraphraser, args, sample_file, args.use_two_path_loss)

                sampled_file_dst = 'logs/intermediate/sampled_out_{}k_{}{}.txt'.format(
                                            iteration//1000, sample_file, args.model_name)
                target_file_dst = 'logs/intermediate/target_out_{}k_{}{}.txt'.format(
                                            iteration//1000, sample_file, args.model_name)
                source_file_dst = 'logs/intermediate/source_out_{}k_{}{}.txt'.format(
                                            iteration//1000, sample_file, args.model_name)
                np.save(sampled_file_dst, np.array(result))
                np.save(target_file_dst, np.array(target))
                np.save(source_file_dst, np.array(source))

                if args.use_two_path_loss:
                    sampled2_file_dst = 'logs/intermediate/sampled2_out_{}k_{}{}.txt'.format(
                                                iteration//1000, sample_file, args.model_name)
                    np.save(sampled2_file_dst, np.array(result))

                print('------------------------------')
                print('results saved to: ')
                print(sampled_file_dst)
                if args.use_two_path_loss:
                    print(sampled2_file_dst)
                print(target_file_dst)
                print(source_file_dst)