#from __future__ import annotations

import numpy as np
import tensorflow as tf

from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential


d_loss_tracker = tf.keras.metrics.Mean ( name = "d_loss" )
"""Metric instance to track the discriminator loss score."""

g_loss_tracker = tf.keras.metrics.Mean ( name = "g_loss" )
"""Metric instance to track the generator loss score."""

c_loss_tracker = tf.keras.metrics.Mean ( name = "c_loss" )
"""Metric instance to track the classifier loss score."""

mse_tracker = tf.keras.metrics.MeanSquaredError ( name = "mse" )
"""Metric instance to track the mean square error."""


class GAN (tf.keras.Model):   # TODO add class description
  """Keras model class to build and train GAN system.
  
  Parameters
  ----------
  X_shape : `int` or array_like
    ...

  Y_shape : `int` or array_like
    ...

  discriminator : `list` of `tf.keras.layers`
    ...

  generator : `list` of `tf.keras.layers`
    ...

  latent_dim : `int`, optional
    ... (`64`, by default).

  Attributes
  ----------
  discriminator : `tf.keras.Sequential`
    ...

  generator : `tf.keras.Sequential`
    ...

  latent_dim : `int`
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
                 X_shape ,
                 Y_shape ,
                 discriminator ,
                 generator     , 
                 classifier = None ,
                 latent_dim = 64 ) -> None:
    super().__init__()
    self._loss_name = "Loss function"

    ## Feature space dimension
    if isinstance ( X_shape, (tuple, list, np.ndarray, tf.Tensor) ):
      X_shape = int ( X_shape[1] )
    if isinstance ( Y_shape, (tuple, list, np.ndarray, tf.Tensor) ):
      Y_shape = int ( Y_shape[1] )

    self._X_shape = X_shape
    self._Y_shape = Y_shape

    ## Data-type control
    if not isinstance (latent_dim, int):
      if isinstance (latent_dim, float): latent_dim = int (latent_dim)
      else: raise TypeError ("The latent space dimension should be an integer.")

    ## Data-value control
    if latent_dim <= 0:
      raise ValueError ("The latent space dimension should be greater than 0.")

    self._latent_dim = latent_dim

    ## Discriminator sequential model
    self._discriminator = Sequential ( name = "discriminator" )
    for d_layer in discriminator:
      self._discriminator . add ( d_layer )
    self._discriminator . add ( Dense ( units = 1, activation = "sigmoid" , 
                                        kernel_initializer = "glorot_normal" ) )

    ## Generator sequential model
    self._generator = Sequential ( name = "generator" )
    for g_layer in generator:
      self._generator . add ( g_layer )
    self._generator . add ( Dense ( units = Y_shape, activation = "linear" ,
                                    kernel_initializer = "glorot_normal" ) )

    ## Classifier sequential model
    if classifier is not None:
      self._classifier = Sequential ( name = "classifier" )
      for c_layer in classifier:
        self._classifier . add ( c_layer )
      self._classifier . add ( Dense ( units = 1, activation = "sigmoid" ,
                                      kernel_initializer = "glorot_normal" ) )
    else:
      self._classifier = None

  def compile ( self , 
                d_optimizer ,
                g_optimizer , 
                c_optimizer = None ,
                d_updt_per_batch = 1 ,
                g_updt_per_batch = 1 ) -> None:   # TODO complete docstring
    """Configure the models for GAN training.
    
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
    super().compile()

    ## Build discriminator and generator models
    self._discriminator . build ( input_shape = (None, self._X_shape + self._Y_shape) )
    self._generator . build ( input_shape = (None, self._X_shape + self._latent_dim) )
    if self._classifier is not None:
      self._classifier . build ( input_shape = (None, self._X_shape + self._Y_shape) )

    ## Data-type control
    if not isinstance (d_updt_per_batch, int):
      if isinstance (d_updt_per_batch, float): d_updt_per_batch = int (d_updt_per_batch)
      else: raise TypeError ("The number of discriminator updates per batch should be an integer.")

    if not isinstance (g_updt_per_batch, int):
      if isinstance (g_updt_per_batch, float): g_updt_per_batch = int (g_updt_per_batch)
      else: raise TypeError ("The number of generator updates per batch should be an integer.")

    ## Data-value control
    if d_updt_per_batch <= 0:
      raise ValueError ("The number of discriminator updates per batch should be greater than 0.")

    if g_updt_per_batch <= 0:
      raise ValueError ("The number of generator updates per batch should be greater than 0.")

    self._d_optimizer = d_optimizer
    self._g_optimizer = g_optimizer
    self._c_optimizer = c_optimizer
    self._d_lr0 = float ( d_optimizer.learning_rate )
    self._g_lr0 = float ( g_optimizer.learning_rate )
    self._c_lr0 = float ( c_optimizer.learning_rate ) if (self._c_optimizer is not None) else None
    self._d_updt_per_batch = d_updt_per_batch
    self._g_updt_per_batch = g_updt_per_batch

  def summary (self) -> None:
    """Print a string summary of the discriminator and generator networks."""
    print ("_" * 65)
    self._discriminator . summary()
    self._generator . summary()
    if self._classifier is not None:
      self._classifier . summary()

  @staticmethod
  def _unpack_data (data):
    """Unpack data-batch into input, output and weights (`None`, if not available)."""
    if len(data) == 4:
      X , Y , w_X , w_Y = data
    else:
      X , Y = data
      w_X = None
      w_Y = None
    return X, Y, w_X, w_Y

  def train_step (self, data) -> dict:
    """Train step for Keras APIs."""
    X, Y, w_X, w_Y = self._unpack_data (data)

    ## Discriminator updates per batch
    for i in range(self._d_updt_per_batch):
      self._train_d_step (X, Y, w_X, w_Y)

    ## Generator updates per batch
    for j in range(self._g_updt_per_batch):
      self._train_g_step (X, Y, w_X, w_Y)

    ## Loss computation
    ref_sample, gen_sample = self._arrange_samples (X, Y, w_X, w_Y)
    d_loss = self._compute_d_loss (gen_sample, ref_sample)
    g_loss = self._compute_g_loss (gen_sample, ref_sample)
    threshold = self._compute_threshold (ref_sample)

    ## Update metrics state
    d_loss_tracker . update_state (d_loss + threshold)
    g_loss_tracker . update_state (g_loss - threshold)

    Y_gen = self.generate (X)
    mse_tracker . update_state (Y, Y_gen, sample_weight = w_Y)

    if self._classifier is None:
      return { "mse"    : mse_tracker.result()    ,
               "d_loss" : d_loss_tracker.result() , 
               "g_loss" : g_loss_tracker.result() ,
               "d_lr"   : self._d_optimizer.lr    ,
               "g_lr"   : self._g_optimizer.lr    }

    ## If classifier enabled
    else:
      self._train_c_step (X, Y, w_X, w_Y)
      c_loss = self._compute_c_loss (gen_sample, ref_sample)
      c_loss_tracker . update_state (c_loss)
      return { "mse"    : mse_tracker.result()    ,
               "c_loss" : c_loss_tracker.result() ,
               "d_loss" : d_loss_tracker.result() , 
               "g_loss" : g_loss_tracker.result() ,
               "d_lr"   : self._d_optimizer.lr    ,
               "g_lr"   : self._g_optimizer.lr    }

  def test_step (self, data) -> dict:
    """Test step for Keras APIs."""
    X, Y, w_X, w_Y = self._unpack_data (data)

    ## Loss computation
    ref_sample, gen_sample = self._arrange_samples (X, Y, w_X, w_Y)
    d_loss = self._compute_d_loss (gen_sample, ref_sample)
    g_loss = self._compute_g_loss (gen_sample, ref_sample)
    threshold = self._compute_threshold (ref_sample)

    ## Update metrics state
    d_loss_tracker . update_state (d_loss + threshold)
    g_loss_tracker . update_state (g_loss - threshold)

    Y_gen = self.generate (X)
    mse_tracker . update_state (Y, Y_gen, sample_weight = w_Y)

    if self._classifier is None:
      return { "mse"    : mse_tracker.result()    ,
               "d_loss" : d_loss_tracker.result() , 
               "g_loss" : g_loss_tracker.result() ,
               "d_lr"   : self._d_optimizer.lr    ,
               "g_lr"   : self._g_optimizer.lr    }
               
    ## If classifier enabled
    else:
      c_loss = self._compute_c_loss (gen_sample, ref_sample)
      c_loss_tracker . update_state (c_loss)
      return { "mse"    : mse_tracker.result()    ,
               "c_loss" : c_loss_tracker.result() ,
               "d_loss" : d_loss_tracker.result() , 
               "g_loss" : g_loss_tracker.result() ,
               "d_lr"   : self._d_optimizer.lr    ,
               "g_lr"   : self._g_optimizer.lr    }

  def _arrange_samples (self, X, Y, w_X = None, w_Y = None) -> tuple:   # TODO complete docstring
    """Arrange the reference and generated samples.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w_X : `tf.Tensor`, optional
      ... (`None`, by default).

    w_Y : `tf.Tensor`, optional
      ... (`None`, by default).
    
    Returns
    -------
    ref_sample : `tuple` of `tf.Tensor`
      ...

    gen_sample : `tuple` of `tf.Tensor`
      ...
    """
    ## Data-batch splitting
    batch_size = tf.cast ( tf.shape(X)[0] / 2, tf.int32 )
    X_ref , X_gen = X[:batch_size], X[batch_size:batch_size*2]
    Y_ref = Y[:batch_size]
    if (w_X is not None) and (w_Y is not None):
      w_ref = w_Y[:batch_size]
      w_gen = w_X[batch_size:batch_size*2]
    else:
      w_ref = tf.ones ( tf.shape(X_ref)[0] )
      w_gen = tf.ones ( tf.shape(X_gen)[0] )

    ## Map the latent space into the generated space
    latent_vectors = tf.random.normal ( shape = (batch_size, self._latent_dim) )
    input_vectors = tf.concat ( [X_gen, latent_vectors], axis = 1 )
    Y_gen = self._generator (input_vectors)

    ## Tensors combination
    XY_ref = tf.concat ( [X_ref, Y_ref], axis = 1 )
    XY_gen = tf.concat ( [X_gen, Y_gen], axis = 1 )

    ## Reference and generated samples
    ref_sample = ( XY_ref, w_ref )
    gen_sample = ( XY_gen, w_gen )
    return ref_sample, gen_sample

  def _train_d_step (self, X, Y, w_X = None, w_Y = None) -> None:   # TODO complete docstring
    """Training step for the discriminator.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w_X : `tf.Tensor`, optional
      ... (`None`, by default).

    w_Y : `tf.Tensor`, optional
      ... (`None`, by default).
    """
    with tf.GradientTape() as tape:
      ref_sample, gen_sample = self._arrange_samples (X, Y, w_X, w_Y)
      d_loss = self._compute_d_loss ( gen_sample, ref_sample )
    grads = tape.gradient ( d_loss, self._discriminator.trainable_weights )
    self._d_optimizer.apply_gradients ( zip (grads, self._discriminator.trainable_weights) )

  def _compute_d_loss (self, gen_sample, ref_sample) -> tf.Tensor:   # TODO complete docstring
    """Return the discriminator loss.
    
    Parameters
    ----------
    gen_sample : `tuple` of `tf.Tensor`
      ...

    ref_sample : `tuple` of `tf.Tensor`
      ...

    Returns
    -------
    d_loss : `tf.Tensor`
      ...
    """
    return - self._compute_g_loss (gen_sample, ref_sample)

  def _train_g_step (self, X, Y, w_X = None, w_Y = None) -> None:   # TODO complete docstring
    """Training step for the generator.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w_X : `tf.Tensor`, optional
      ... (`None`, by default).

    w_Y : `tf.Tensor`, optional
      ... (`None`, by default).
    """
    with tf.GradientTape() as tape:
      ref_sample, gen_sample = self._arrange_samples (X, Y, w_X, w_Y)
      g_loss = self._compute_g_loss ( gen_sample, ref_sample )
    grads = tape.gradient ( g_loss, self._generator.trainable_weights )
    self._g_optimizer.apply_gradients ( zip (grads, self._generator.trainable_weights) )

  def _compute_g_loss (self, gen_sample, ref_sample) -> tf.Tensor:   # TODO complete docstring
    """Return the generator loss.
    
    Parameters
    ----------
    gen_sample : `tuple` of `tf.Tensor`
      ...

    ref_sample : `tuple` of `tf.Tensor`
      ...

    Returns
    -------
    g_loss : `tf.Tensor`
      ...
    """
    ## Extract input tensors and weights
    XY_gen, w_gen = gen_sample
    XY_ref, w_ref = ref_sample

    ## Noise injection to stabilize GAN training
    rnd_gen = tf.random.normal ( tf.shape(XY_gen), mean = 0., stddev = 0.05 )
    rnd_ref = tf.random.normal ( tf.shape(XY_ref), mean = 0., stddev = 0.05 )
    D_gen = self._discriminator ( XY_gen + rnd_gen )
    D_ref = self._discriminator ( XY_ref + rnd_ref )

    ## Loss computation
    g_loss = w_gen * tf.math.log ( tf.clip_by_value ( 1 - D_gen , 1e-12 , 1.0 ) ) + \
             w_ref * tf.math.log ( tf.clip_by_value ( D_ref     , 1e-12 , 1.0 ) )
    return tf.reduce_mean (g_loss)

  def _compute_threshold (self, ref_sample) -> tf.Tensor:   # TODO complete docstring
    """Return the threshold for loss values.
    
    Parameters
    ----------
    ref_sample : `tuple` of `tf.Tensor`
      ...

    Returns
    -------
    th_loss : `tf.Tensor`
      ...
    """
    ## Extract input tensors and weights
    XY_ref, w_ref = ref_sample

    ## Noise injection to stabilize GAN training
    rnd_ref = tf.random.normal ( tf.shape(XY_ref), mean = 0., stddev = 0.05 )
    D_ref = self._discriminator ( XY_ref + rnd_ref )

    ## Split tensors and weights
    batch_size = tf.cast ( tf.shape(XY_ref)[0] / 2, tf.int32 )
    D_ref_1, D_ref_2 = D_ref[:batch_size], D_ref[batch_size:batch_size*2]
    w_ref_1, w_ref_2 = w_ref[:batch_size], w_ref[batch_size:batch_size*2]

    ## Threshold loss computation
    th_loss = w_ref_1 * tf.math.log ( tf.clip_by_value ( D_ref_1     , 1e-12 , 1.0 ) ) + \
              w_ref_2 * tf.math.log ( tf.clip_by_value ( 1 - D_ref_2 , 1e-12 , 1.0 ) )
    return tf.reduce_mean (th_loss)

  def _train_c_step (self, X, Y, w_X = None, w_Y = None) -> None:   # TODO complete docstring
    """Training step for the classifier.
    
    Parameters
    ----------
    X : `tf.Tensor`
      ...

    Y : `tf.Tensor`
      ...

    w_X : `tf.Tensor`, optional
      ... (`None`, by default).

    w_Y : `tf.Tensor`, optional
      ... (`None`, by default).
    """
    with tf.GradientTape() as tape:
      ref_sample, gen_sample = self._arrange_samples (X, Y, w_X, w_Y)
      c_loss = self._compute_c_loss ( gen_sample, ref_sample )
    grads = tape.gradient ( c_loss, self._classifier.trainable_weights )
    self._c_optimizer.apply_gradients ( zip (grads, self._classifier.trainable_weights) )

  def _compute_c_loss (self, gen_sample, ref_sample) -> tf.Tensor:   # TODO complete docstring
    """Return the classifier loss.
    
    Parameters
    ----------
    gen_sample : `tuple` of `tf.Tensor`
      ...

    ref_sample : `tuple` of `tf.Tensor`
      ...

    Returns
    -------
    c_loss : `tf.Tensor`
      ...
    """
    ## Extract input tensors and weights
    XY_gen, w_gen = gen_sample
    XY_ref, w_ref = ref_sample

    ## Classifier output to gen and ref output
    C_gen = self._classifier ( XY_gen )
    C_ref = self._classifier ( XY_ref )

    ## Loss computation
    k_gen = 0.1
    k_ref = 0.9
    c_loss = w_gen * k_gen       * tf.math.log ( tf.clip_by_value ( C_gen     , 1e-12 , 1.0 ) ) + \
             w_gen * (1 - k_gen) * tf.math.log ( tf.clip_by_value ( 1 - C_gen , 1e-12 , 1.0 ) ) + \
             w_ref * k_ref       * tf.math.log ( tf.clip_by_value ( C_ref     , 1e-12 , 1.0 ) ) + \
             w_ref * (1 - k_ref) * tf.math.log ( tf.clip_by_value ( 1 - C_ref , 1e-12 , 1.0 ) ) 
    return - tf.reduce_mean (c_loss)

  def generate (self, X) -> tf.Tensor:   # TODO complete docstring
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
    latent_dim = self.latent_dim
    latent_tensor = tf.random.normal ( shape = (batch_size, latent_dim) )

    ## Map the latent space into the generated space
    input_tensor = tf.concat ( [X, latent_tensor], axis = 1 )
    Y_gen = self.generator (input_tensor)
    return Y_gen

  @property
  def loss_name (self) -> str:
    """Name of the loss function used for training."""
    return self._loss_name

  @property
  def discriminator (self) -> tf.keras.Sequential:
    """The discriminator of the GAN system."""
    return self._discriminator

  @property
  def generator (self) -> tf.keras.Sequential:
    """The generator of the GAN system."""
    return self._generator

  @property
  def classifier (self) -> tf.keras.Sequential:
    """The classifier of the GAN two-players game."""
    return self._classifier

  @property
  def latent_dim (self) -> int:
    """The dimension of the latent space."""
    return self._latent_dim

  @property
  def d_optimizer (self) -> tf.keras.optimizers.Optimizer:
    """The discriminator optimizer."""
    return self._d_optimizer

  @property
  def g_optimizer (self) -> tf.keras.optimizers.Optimizer:
    """The generator optimizer."""
    return self._g_optimizer

  @property
  def c_optimizer (self) -> tf.keras.optimizers.Optimizer:
    """The classifier optimizer."""
    return self._c_optimizer

  @property
  def d_lr0 (self) -> float:
    """Initial value for discriminator learning rate."""
    return self._d_lr0

  @property
  def g_lr0 (self) -> float:
    """Initial value for generator learning rate."""
    return self._g_lr0

  @property
  def c_lr0 (self) -> float:
    """Initial value for classifier learning rate."""
    return self._c_lr0

  @property
  def g_updt_per_batch (self) -> int:
    """Number of generator updates per batch."""
    return self._g_updt_per_batch

  @property
  def d_updt_per_batch (self) -> int:
    """Number of discriminator updates per batch."""
    return self._d_updt_per_batch

  @property
  def metrics (self) -> list:
    return [d_loss_tracker, g_loss_tracker, mse_tracker]
