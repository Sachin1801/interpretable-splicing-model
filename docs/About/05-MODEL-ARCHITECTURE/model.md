# model.py - Detailed Explanation

**Purpose:** Defines the neural network architecture, custom layers, loss functions, and regularizers.

**Location:** `/model_training/model.py`

---

## Custom Layer Classes

### Selector Class (Lines 22-57)

A layer that selects one output from multiple inputs using non-trainable weights.

```python
@tf.keras.utils.register_keras_serializable()
class Selector(Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        # Initialize selector weights: first input selected by default
        # e.g., [1, 0, 0] for 3 inputs
        self.selectors = self.add_weight(
            name="selectors",
            shape=(len(input_shape),),
            initializer=selector_init,  # [1, 0, 0, ...]
            trainable=False,  # Not trained, set programmatically
        )

    def call(self, x):
        # Weighted sum of inputs
        return sum([self.selectors[i] * x[i] for i in range(len(x))])
```

**Purpose:** Enables three-step training by switching which output branch is active.

**Usage in training:**
```python
# Step 1: Train sequence branch
model.get_layer("output_selector").set_weights([np.array([1, 0, 0])])

# Step 2: Train structure branch
model.get_layer("output_selector").set_weights([np.array([0, 1, 0])])

# Step 3: Train residual tuner
model.get_layer("output_selector").set_weights([np.array([0, 0, 1])])
```

---

### ResidualTuner Class (Lines 60-88)

A residual MLP block for fine-tuning predictions.

```python
@tf.keras.utils.register_keras_serializable()
class ResidualTuner(Layer):
    def __init__(self, hidden_units=100, **kwargs):
        super().__init__(**kwargs)
        self.hidden_units = hidden_units
        # Create layers
        self.dense1 = Dense(self.hidden_units, activation="relu")
        self.batchnorm1 = BatchNormalization()
        self.dense2 = Dense(self.hidden_units, activation="relu")
        self.batchnorm2 = BatchNormalization()
        self.dense3 = Dense(1)

    def call(self, inp):
        x = self.dense1(inp)
        x = self.batchnorm1(x)
        x = self.dense2(x)
        x = self.batchnorm2(x)
        x = self.dense3(x)
        return x + inp  # Residual connection
```

**Architecture:**
```
input → Dense(4) → BN → ReLU → Dense(4) → BN → ReLU → Dense(1) → ADD(input) → output
```

**Purpose:** Allows the model to learn small corrections to the energy-based prediction. The residual connection ensures the base prediction is preserved.

---

### SumDiff Class (Lines 91-131)

Computes the energy difference between inclusion and skipping.

```python
@tf.keras.utils.register_keras_serializable()
class SumDiff(Layer):
    def __init__(self, freeze=False, **kwargs):
        super().__init__(**kwargs)
        self.freeze = freeze

    def build(self, input_shape):
        # Bias term
        self.b = self.add_weight(
            name="b",
            shape=(1,),
            initializer=tf.keras.initializers.Zeros(),
            trainable=not self.freeze,
        )
        # Scale term
        self.w = self.add_weight(
            name="w",
            shape=(1,),
            initializer=tf.keras.initializers.Ones(),
            trainable=not self.freeze,
        )

    def call(self, x):
        # x[0] = inclusion activations, x[1] = skipping activations
        # Sum all positions and filters, then compute difference
        out = tf.reduce_sum(x[0], axis=(1, 2)) - tf.reduce_sum(x[1], axis=(1, 2))
        return self.b + self.w * tf.reshape(out, shape=(-1, 1))
```

**Formula:**
```
energy = w * (sum(inclusion_activations) - sum(skipping_activations)) + b
```

**Interpretation:**
- High energy → more inclusion
- Low energy → more skipping
- The sigmoid converts energy to PSI probability

---

### RegularizedBiasLayer Class (Lines 214-267)

Adds position-specific learnable biases with smoothness regularization.

```python
@tf.keras.utils.register_keras_serializable()
class RegularizedBiasLayer(Layer):
    def __init__(
        self,
        position_regularization,
        adjacency_regularization_fo,
        adjacency_regularization_so,
        adjacency_left_trim=0,
        adjacency_right_trim=0,
        **kwargs
    ):
        super().__init__(**kwargs)
        # Store regularization parameters
        self.position_regularization = position_regularization
        self.adjacency_regularization_fo = adjacency_regularization_fo
        self.adjacency_regularization_so = adjacency_regularization_so
        self.adjacency_left_trim = adjacency_left_trim
        self.adjacency_right_trim = adjacency_right_trim

    def build(self, input_shape):
        # Create regularizer
        regularizer = MultiRegularizer(...)

        # Create position bias weights
        self.kernel = self.add_weight(
            name="kernel",
            shape=(input_shape[1], input_shape[2]),  # (positions, filters)
            initializer="random_normal",
            regularizer=regularizer,
            trainable=True,
        )

    def call(self, x):
        return self.kernel + x  # Add bias to input
```

**Purpose:** Each position × filter combination has a learnable bias. The regularizer ensures these biases vary smoothly across positions.

---

## Regularization Functions

### pos_reg (Lines 144-147) - Position Regularization

```python
def pos_reg(x, adjacency_left_trim=0, adjacency_right_trim=0):
    l = x.shape[0]
    return tf.reduce_sum(tf.square(x[adjacency_left_trim : l - adjacency_right_trim]))
```

**Formula:** `sum(w²)` - Standard L2 regularization on position biases.

---

### adj_reg_fo (Lines 150-158) - First-Order Adjacency

```python
def adj_reg_fo(x, adjacency_left_trim=0, adjacency_right_trim=0):
    l = x.shape[0]
    x_trimmed = x[adjacency_left_trim : l - adjacency_right_trim]
    x_norm = x_trimmed - tf.reduce_mean(x_trimmed, axis=0)
    A = tf.reduce_sum((x_norm[:-1] - x_norm[1:]) ** 2, axis=0)
    B = tf.reduce_sum(x_norm ** 2, axis=0)
    return tf.reduce_mean(A / B)
```

**Formula:** `sum((w[i+1] - w[i])²) / sum(w²)`

**Purpose:** Penalizes rapid changes between adjacent positions. Encourages smooth position biases.

---

### adj_reg_so (Lines 161-171) - Second-Order Adjacency

```python
def adj_reg_so(x, adjacency_left_trim=0, adjacency_right_trim=0):
    l = x.shape[0]
    x_trimmed = x[adjacency_left_trim : l - adjacency_right_trim]
    x_norm = x_trimmed - tf.reduce_mean(x_trimmed, axis=0)
    diff_1 = x_norm[:-1] - x_norm[1:]
    diff_2 = diff_1[:-1] - diff_1[1:]  # Second difference
    A = tf.reduce_sum(diff_2 ** 2, axis=0)
    B = tf.reduce_sum(x_norm ** 2, axis=0)
    return tf.reduce_mean(A / B)
```

**Formula:** `sum((w[i+2] - 2*w[i+1] + w[i])²) / sum(w²)`

**Purpose:** Penalizes changes in the *rate of change* of position biases. Encourages linear or constant trends.

---

## Loss Function

### binary_KL (Lines 134-141)

```python
@tf.keras.utils.register_keras_serializable()
def binary_KL(y_true, y_pred):
    return tf.keras.backend.mean(
        tf.keras.backend.binary_crossentropy(y_true, y_pred)
        - tf.keras.backend.binary_crossentropy(y_true, y_true),
        axis=-1,
    )
```

**Formula:**
```
binary_KL = mean(BCE(y_true, y_pred) - BCE(y_true, y_true))
         = mean(y_true * log(y_true/y_pred) + (1-y_true) * log((1-y_true)/(1-y_pred)))
```

This is the KL divergence between two Bernoulli distributions.

**Why use this instead of MSE?**
- Better calibrated probability predictions
- More sensitive to errors at extreme PSI values (near 0 or 1)
- Information-theoretic interpretation

---

## Model Construction: get_model() (Lines 319-490)

### Input Layers

```python
seq_input = Input(shape=(input_length, 4), name="seq_input")
struct_input = Input(shape=(input_length, 3), name="struct_input")
wobble_input = Input(shape=(input_length, 1), name="wobble_input")
```

### Sequence Branch

```python
# Convolutional filters for inclusion
qc_incl = Conv1D(filters=num_filters, kernel_size=filter_width, name="qc_incl")
out_simple_incl = qc_incl(seq_input)

# Position-specific bias
position_bias_incl = RegularizedBiasLayer(...)
biased_incl = position_bias_incl(out_simple_incl)

# Dropout
dropout_bias_incl = Dropout(dropout_rate)(biased_incl)
```

Same for skipping branch with `qc_skip`.

### Structure Branch

```python
# Concatenate all inputs
concat_input = Concatenate()([seq_input, struct_input, wobble_input])

# Larger convolutional filters for structure
c_incl_struct = Conv1D(num_structure_filters, structure_filter_width, padding="same")
structure_out_incl = c_incl_struct(concat_input)

# Position bias and dropout
structure_out_incl = position_bias_incl_struct(structure_out_incl)
structure_out_incl = dropout_incl_struct(structure_out_incl)

# Trim edges (structure filters have wide receptive field)
structure_out_incl = structure_out_incl[:, 2:-3, :]
```

### Energy Computation

```python
# Sequence-only energy
energy_seq_out = energy_seq([
    regularized_act(dropout_bias_incl, activity_regularization, activation="softplus"),
    regularized_act(dropout_bias_skip, activity_regularization, activation="softplus"),
])

# Sequence + structure energy
seq_struct_concat_incl = Concatenate()([dropout_bias_incl, structure_out_incl])
seq_struct_concat_skip = Concatenate()([dropout_bias_skip, structure_out_skip])

energy_seq_struct_out = energy_seq_struct([
    regularized_act(seq_struct_concat_incl, activity_regularization, activation="softplus"),
    regularized_act(seq_struct_concat_skip, activity_regularization, activation="softplus"),
])
```

### Output

```python
# Residual fine-tuning
gen_func_out = gen_func(energy_seq_struct_out)

# Select output based on training step
selected = output_selector([energy_seq_out, energy_seq_struct_out, gen_func_out])

# Final sigmoid for PSI prediction
out = Activation("sigmoid")(selected)

# Create and compile model
model = Model(inputs=[seq_input, struct_input, wobble_input], outputs=out)
model.compile(optimizer="adam", loss=binary_KL, metrics=[binary_KL])
```

---

## Model Summary

```
Layer (type)                 Output Shape              Param #
================================================================
seq_input (InputLayer)       [(None, 90, 4)]           0
struct_input (InputLayer)    [(None, 90, 3)]           0
wobble_input (InputLayer)    [(None, 90, 1)]           0
qc_incl (Conv1D)             (None, 85, 20)            500
qc_skip (Conv1D)             (None, 85, 20)            500
position_bias_incl           (None, 85, 20)            1700
position_bias_skip           (None, 85, 20)            1700
concatenate (Concatenate)    (None, 90, 8)             0
c_incl_struct (Conv1D)       (None, 90, 8)             1928
c_skip_struct (Conv1D)       (None, 90, 8)             1928
position_bias_incl_struct    (None, 90, 8)             720
position_bias_skip_struct    (None, 90, 8)             720
energy_seq (SumDiff)         (None, 1)                 2
energy_seq_struct (SumDiff)  (None, 1)                 2
gen_func (ResidualTuner)     (None, 1)                 54
output_selector (Selector)   (None, 1)                 3
output_activation (Sigmoid)  (None, 1)                 0
================================================================
Total params: ~9,757
Trainable params: ~9,754
Non-trainable params: 3 (selector weights)
```
