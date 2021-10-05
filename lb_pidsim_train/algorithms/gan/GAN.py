from __future__ import annotations

import os
import numpy as np
import tensorflow as tf
import matplotlib as mpl
import matplotlib.pyplot as plt


d_loss_tracker = tf.keras.metrics.Mean ( name = "d_loss" )
"""Metric instance to track the discriminator loss score."""

g_loss_tracker = tf.keras.metrics.Mean ( name = "g_loss" )
"""Metric instance to track the generator loss score."""


class GAN (tf.keras.Model):
  """Keras model class to build and train GAN system.
  
  Parameters
  ----------
  discriminator : `tf.keras.Sequential`
    ...

  generator : `tf.keras.Sequential`
    ...

  latent_dim : `int`, optional
    ... (`64`, by default).

  Attributes
  ----------
  discriminator : `tf.keras.Sequential`
    ...

  generator : `tf.keras.Sequential`
    ...

  Notes
  -----
  ...

  References
  ----------
  ...

  See Also
  --------
  ...

  Methods
  -------
  ...
  """
  def __init__ ( self , 
                 discriminator ,
                 generator     , 
                 latent_dim = 64 ) -> None:
    super(GAN, self) . __init__()
    self._discriminator = discriminator
    self._generator = generator
    self._latent_dim = latent_dim

  def compile ( self , 
                d_optimizer ,
                g_optimizer , 
                d_updt_per_batch = 1 ,
                g_updt_per_batch = 1 ) -> None:
    """Configure the models for training.
    
    Parameters
    ----------
    d_optimizer : `tf.keras.optimizers.Optimizer`
      ...

    g_optimizer : `tf.keras.optimizers.Optimizer`
      ...

    d_updt_per_batch : `int`, optional
      ... (`1`, by default).

    g_updt_per_batch : `int`, optional
      ... (`1`, by default).
    """
    super(GAN, self) . compile()
    self._d_optimizer = d_optimizer
    self._g_optimizer = g_optimizer

    ## Data-type control
    try:
      d_updt_per_batch = int ( d_updt_per_batch )
    except:
      raise ValueError ("The number of discriminator updates per batch should be an integer.")
    try:
      g_updt_per_batch = int ( g_updt_per_batch )
    except:
      raise ValueError ("The number of generator updates per batch should be an integer.")

    ## Data-value control
    if d_updt_per_batch == 0:
      raise ValueError ("The number of discriminator updates per batch should be greater than 0.")
    if g_updt_per_batch == 0:
      raise ValueError ("The number of generator updates per batch should be greater than 0.")

    self._d_updt_per_batch = d_updt_per_batch
    self._g_updt_per_batch = g_updt_per_batch

  @staticmethod
  def _unpack_data (data):
    """Unpack data-batch into input, output and weights (`None`, if not available)."""
    if len(data) == 3:
      X , Y , w = data
    else:
      X , Y = data
      w = None
    return X, Y, w

  def train_step (self, data) -> dict:
    """Train step for Keras APIs."""
    X, Y, w = self._unpack_data (data)

    ## Discriminator updates per batch
    for i in range(self._d_updt_per_batch):
      self._train_d_step (X, Y, w)

    ## Generator updates per batch
    for j in range(self._g_updt_per_batch):
      self._train_g_step (X, Y, w)

    ref_sample, gen_sample = self._arrange_samples (X, Y)
    d_loss = self._compute_d_loss (gen_sample, ref_sample, weights = w)
    g_loss = self._compute_g_loss (gen_sample, ref_sample, weights = w)

    d_loss_tracker . update_state (d_loss)
    g_loss_tracker . update_state (g_loss)
    return {"d_loss": d_loss_tracker.result(), "g_loss": g_loss_tracker.result()}

  def test_step (self, data) -> dict:
    """Test step for Keras APIs."""
    X, Y, w = self._unpack_data (data)

    ref_sample, gen_sample = self._arrange_samples (X, Y)
    d_loss = self._compute_d_loss (gen_sample, ref_sample, weights = w)
    g_loss = self._compute_g_loss (gen_sample, ref_sample, weights = w)

    d_loss_tracker . update_state (d_loss)
    g_loss_tracker . update_state (g_loss)
    return {"d_loss": d_loss_tracker.result(), "g_loss": g_loss_tracker.result()}

  def _arrange_samples (self, X, Y) -> tuple:
    """Arrange the reference and generated samples.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...
    
    Returns
    -------
    ref_sample : `tf.Tensor`
      ...

    gen_sample : `tf.Tensor`
      ...
    """
    ## Sample random points in the latent space
    batch_size = tf.shape(X)[0]
    latent_vectors = tf.random.normal ( shape = (batch_size, self._latent_dim) )

    ## Map the latent space into the generated space
    input_vectors = tf.concat ( [X, latent_vectors], axis = 1 )
    generated = self._generator (input_vectors)

    ## Reference and generated sample
    ref_sample = tf.concat ( [X, Y], axis = 1 )
    gen_sample = tf.concat ( [X, generated], axis = 1 )
    return ref_sample, gen_sample

  @tf.function
  def _train_d_step (self, X, Y, w = None) -> None:
    """Training step for the discriminator.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w : `tf.Tensor`, optional
      ... (`None`, by default).
    """
    with tf.GradientTape() as tape:
      ref_sample, gen_sample = self._arrange_samples (X, Y)
      d_loss = self._compute_d_loss ( gen_sample, ref_sample, weights = w )
    grads = tape.gradient ( d_loss, self._discriminator.trainable_weights )
    self._d_optimizer.apply_gradients ( zip (grads, self._discriminator.trainable_weights) )

  def _compute_d_loss (self, gen_sample, ref_sample, weights = None) -> tf.Tensor:
    """Return the discriminator loss.
    
    Parameters
    ----------
    gen_sample : `tf.Tensor`
      ...

    ref_sample : `tf.Tensor`
      ...

    weights : `tf.Tensor`
      ...

    Returns
    -------
    d_loss : `tf.Tensor`
      ...
    """
    loss = - self._compute_g_loss (gen_sample, ref_sample, weights)
    if weights is not None:
      loss = weights * loss
    return tf.reduce_mean (loss)

  @tf.function
  def _train_g_step (self, X, Y, w = None) -> None:
    """Training step for the generator.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w : `tf.Tensor`, optional
      ... (`None`, by default).
    """
    with tf.GradientTape() as tape:
      ref_sample, gen_sample = self._arrange_samples (X, Y)
      g_loss = self._compute_g_loss ( gen_sample, ref_sample, weights = w )
    grads = tape.gradient ( g_loss, self._generator.trainable_weights )
    self._g_optimizer.apply_gradients ( zip (grads, self._generator.trainable_weights) )

  def _compute_g_loss (self, gen_sample, ref_sample, weights = None) -> tf.Tensor:
    """Return the generator loss.
    
    Parameters
    ----------
    gen_sample : `tf.Tensor`
      ...

    ref_sample : `tf.Tensor`
      ...

    weights : `tf.Tensor`
      ...

    Returns
    -------
    d_loss : `tf.Tensor`
      ...
    """
    ## Noise injection to stabilize GAN training
    rnd_gen = tf.random.normal ( tf.shape(gen_sample), mean = 0., stddev = 0.1 )
    rnd_ref = tf.random.normal ( tf.shape(ref_sample), mean = 0., stddev = 0.1 )
    D_gen = self._discriminator ( gen_sample + rnd_gen )
    D_ref = self._discriminator ( ref_sample + rnd_ref )

    ## Loss computation
    loss = tf.math.log ( tf.clip_by_value (D_ref, 1e-12, 1.) * tf.clip_by_value (1 - D_gen, 1e-12, 1.) )
    if weights is not None:
      loss = weights * loss
    return tf.reduce_mean (loss)

  def generate (self, X) -> tf.Tensor:
    """Method to generate the target variables `Y` given the input features `X`.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Returns
    -------
    Y_gen : `tf.Tensor`
      ...
    """
    ## Sample random points in the latent space
    batch_size = tf.shape(X)[0]
    latent_vectors = tf.random.normal ( shape = (batch_size, self._latent_dim) )

    ## Map the latent space into the generated space
    input_vectors = tf.concat ( [X, latent_vectors], axis = 1 )
    generated = self._generator (input_vectors)
    return generated

  @property
  def discriminator (self) -> tf.keras.Sequential:
    """The discriminator of the GAN system."""
    return self._discriminator

  @property
  def generator (self) -> tf.keras.Sequential:
    """The generator of the GAN system."""
    return self._generator

  @property
  def metrics (self) -> list:
    return [d_loss_tracker, g_loss_tracker]
