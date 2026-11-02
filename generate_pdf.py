import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

output_pdf = os.path.abspath("machine-learning-and-deep-learning-notes.pdf")

doc = SimpleDocTemplate(
    output_pdf,
    pagesize=letter,
    rightMargin=45,
    leftMargin=45,
    topMargin=40,
    bottomMargin=40
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=colors.HexColor("#1D1D1F"),
    spaceAfter=10
)

subtitle_style = ParagraphStyle(
    "DocSubTitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#6E6E73"),
    spaceAfter=15
)

h1_style = ParagraphStyle(
    "Heading1",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    textColor=colors.HexColor("#0071E3"),
    spaceBefore=8,
    spaceAfter=4
)

h2_style = ParagraphStyle(
    "Heading2",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=colors.HexColor("#1D1D1F"),
    spaceBefore=6,
    spaceAfter=2
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12.5,
    textColor=colors.HexColor("#2C2C2E"),
    spaceAfter=6
)

bullet_style = ParagraphStyle(
    "Bullet",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor("#2C2C2E"),
    leftIndent=12,
    spaceAfter=3
)

story = []

# ==================== PAGE 1: Foundations of Machine Learning ====================
story.append(Paragraph("Machine Learning & Deep Learning: Comprehensive Course Notes", title_style))
story.append(Paragraph("Unit 1: Foundations of Machine Learning — Supervised, Unsupervised, and Statistical Learning", subtitle_style))

story.append(Paragraph("1.1 Definition & Paradigms of Learning", h1_style))
story.append(Paragraph(
    "Machine Learning (ML) is the computational study of algorithms that improve their performance at specific tasks through empirical data rather than rule-based programming (Tom Mitchell, 1997). The three primary learning paradigms are:",
    body_style
))
story.append(Paragraph("• <b>Supervised Learning:</b> The algorithm learns a mapping function f: X → Y from labeled input-output pairs. Primary tasks include Regression (predicting continuous outputs like house prices or temperature) and Classification (predicting categorical labels like spam detection or disease diagnosis).", bullet_style))
story.append(Paragraph("• <b>Unsupervised Learning:</b> The model uncovers latent geometric structures, probability distributions, or clusters in unlabeled data X without supervisor targets. Key techniques include Clustering (K-Means, DBSCAN, Hierarchical) and Dimensionality Reduction (Principal Component Analysis / PCA, t-SNE, UMAP).", bullet_style))
story.append(Paragraph("• <b>Reinforcement Learning (RL):</b> An autonomous agent learns optimal policies π(a|s) through sequential trial-and-error interactions with a dynamic environment to maximize cumulative discounted reward signals.", bullet_style))

story.append(Paragraph("1.2 The Generalization Problem & Bias-Variance Tradeoff", h1_style))
story.append(Paragraph(
    "The central goal of machine learning is generalization: achieving low risk on unseen data drawn from the same underlying distribution. The total expected generalization error decomposes into three additive terms:",
    body_style
))
story.append(Paragraph("<b>Total Expected Error = Bias² + Variance + Irreducible Error (σ²)</b>", body_style))
story.append(Paragraph("• <b>High Bias (Underfitting):</b> The learning algorithm makes overly simplistic assumptions about the target function, failing to capture true non-linear patterns (e.g., fitting a straight line to sinusoidal data). Both training and test errors are high.", bullet_style))
story.append(Paragraph("• <b>High Variance (Overfitting):</b> The model is excessively flexible and fits statistical noise or sample-specific idiosyncrasies rather than the true underlying distribution. Training error is very low, but validation/test error is high.", bullet_style))
story.append(Paragraph("• <b>Regularization:</b> Penalizing model complexity to control variance. L1 Regularization (Lasso, adds λ||w||₁) drives uninformative weights strictly to zero, performing automated feature selection. L2 Regularization (Ridge / Weight Decay, adds λ||w||₂²) shrinks weight magnitudes toward zero, stabilizing multicollinearity.", bullet_style))

story.append(Paragraph("1.3 Core Classical Machine Learning Algorithms", h1_style))
story.append(Paragraph("• <b>Linear & Logistic Regression:</b> Linear regression models E[Y|X] = Xw via Ordinary Least Squares (OLS) or Gradient Descent. Logistic regression models the probability of binary classes using the Sigmoid link function: P(Y=1|X) = 1 / (1 + e^(-Xw)), trained via Binary Cross-Entropy (Log-Loss).", bullet_style))
story.append(Paragraph("• <b>Decision Trees & Ensembles:</b> Decision Trees recursively partition feature space by maximizing Information Gain (entropy reduction) or Gini Impurity. <b>Random Forests</b> aggregate decorrelated decision trees via Bootstrap Aggregation (bagging), drastically reducing variance. <b>Gradient Boosting Machines (XGBoost, LightGBM)</b> iteratively train weak learners to minimize pseudo-residuals of the existing ensemble.", bullet_style))
story.append(Paragraph("• <b>Support Vector Machines (SVM):</b> Finds the optimal separating hyperplane that maximizes the geometric margin between decision boundaries and support vectors. Non-linear classification is enabled by the Kernel Trick (e.g., Radial Basis Function / RBF kernel), mapping inputs into infinite-dimensional Hilbert spaces without explicit coordinate transformations.", bullet_style))

story.append(PageBreak())

# ==================== PAGE 2: Neural Networks & Deep Learning Core ====================
story.append(Paragraph("Unit 2: Neural Networks & Deep Learning Fundamentals", title_style))
story.append(Paragraph("Artificial Neurons, Non-Linear Activations, Backpropagation, and Optimization", subtitle_style))

story.append(Paragraph("2.1 The Artificial Neuron & Multilayer Perceptrons", h1_style))
story.append(Paragraph(
    "Artificial Neural Networks (ANNs) consist of interconnected processing units modeled after biological neurons. A single neuron calculates a weighted linear combination of inputs followed by a scalar non-linear activation function:",
    body_style
))
story.append(Paragraph("<b>z = ∑ (w_i · x_i) + b = w^T x + b,    a = σ(z)</b>", body_style))
story.append(Paragraph(
    "The <b>Universal Approximation Theorem</b> (Cybenko, 1989; Hornik, 1991) establishes that a feedforward network with a single hidden layer containing finite non-linear neurons can approximate any continuous function on compact subsets of R^n to arbitrary precision.",
    body_style
))

story.append(Paragraph("2.2 Non-Linear Activation Functions", h1_style))
story.append(Paragraph("Activation functions inject non-linearity, allowing deep networks to compute non-linear manifolds and composite representations:", body_style))
story.append(Paragraph("• <b>Sigmoid (Logistic):</b> σ(z) = 1 / (1 + e^(-z)). Maps inputs to range (0, 1). Suffers severely from the vanishing gradient problem because derivatives approach zero for |z| > 4.", bullet_style))
story.append(Paragraph("• <b>Hyperbolic Tangent (Tanh):</b> tanh(z) = (e^z - e^(-z)) / (e^z + e^(-z)). Zero-centered output in range (-1, 1). Better than sigmoid for intermediate layers, but still saturates at extremes.", bullet_style))
story.append(Paragraph("• <b>Rectified Linear Unit (ReLU):</b> f(z) = max(0, z). The industry standard for hidden layers. It eliminates vanishing gradients for positive inputs, enables sparse activations, and computes exceptionally fast. The 'Dying ReLU' problem occurs when neurons output 0 for all inputs due to large negative biases.", bullet_style))
story.append(Paragraph("• <b>Leaky ReLU & GELU:</b> Leaky ReLU introduces a small positive slope (e.g., 0.01z) for z < 0. Gaussian Error Linear Unit (GELU) weights inputs by their normal cumulative distribution, utilized in modern transformer models like BERT and GPT.", bullet_style))
story.append(Paragraph("• <b>Softmax:</b> Used in categorical multi-class output layers: P(Y=k|z) = e^(z_k) / ∑ e^(z_j), transforming raw logit scores into a normalized probability distribution summing to 1.0.", bullet_style))

story.append(Paragraph("2.3 Loss Functions & Backpropagation", h1_style))
story.append(Paragraph(
    "Neural network parameters (weights W and biases b) are optimized by minimizing an empirical risk loss function L(y_true, y_pred). Common loss functions include <b>Mean Squared Error (MSE)</b> for continuous targets and <b>Categorical Cross-Entropy Loss</b>: L = -∑ y_k log(y_pred_k) for classification.",
    body_style
))
story.append(Paragraph(
    "<b>Backpropagation</b> is an exact and efficient implementation of the multivariate calculus chain rule. For each layer l, the error gradient δ^l = ∂L/∂z^l is recursively propagated backwards from output layer L to input layer 1:",
    body_style
))
story.append(Paragraph("<b>δ^l = ((W^(l+1))^T · δ^(l+1)) ⊙ σ'(z^l),    ∂L/∂W^l = δ^l · (a^(l-1))^T</b>", body_style))

story.append(Paragraph("2.4 Gradient-Based Optimization Algorithms", h1_style))
story.append(Paragraph("• <b>Stochastic Gradient Descent (SGD):</b> Updates parameters using minibatches of data: θ ← θ - η · ∇_θ L_B. Fast, but oscillates in ravines of ill-conditioned curvature.", bullet_style))
story.append(Paragraph("• <b>Momentum:</b> Accumulates an exponentially decaying moving average of past gradients (v_t = γ v_(t-1) + η ∇L), dampening high-frequency oscillations and accelerating through saddle points.", bullet_style))
story.append(Paragraph("• <b>Adam (Adaptive Moment Estimation):</b> Combines Momentum (first moment estimation m_t) and RMSprop (second moment uncentered variance estimation v_t) with bias corrections: θ ← θ - (η / (sqrt(v̂_t) + ε)) · m̂_t. Adam is the default optimizer for deep learning.", bullet_style))

story.append(PageBreak())

# ==================== PAGE 3: Deep Learning Architectures ====================
story.append(Paragraph("Unit 3: Modern Deep Learning Architectures", title_style))
story.append(Paragraph("Convolutional Neural Networks, Recurrent Networks, and the Transformer Revolution", subtitle_style))

story.append(Paragraph("3.1 Convolutional Neural Networks (CNNs) for Spatial Data", h1_style))
story.append(Paragraph(
    "CNNs exploit spatial translation invariance and local pixel correlations through parameter sharing and sparse connectivity, drastically reducing parameter counts compared to dense networks:",
    body_style
))
story.append(Paragraph("• <b>Discrete Convolution Operation:</b> A small learnable tensor kernel K of size (k_h × k_w) slides across the input tensor X with stride s and zero-padding p, computing localized dot products: S(i,j) = (X * K)(i,j) = ∑ ∑ X(i-m, j-n) K(m,n).", bullet_style))
story.append(Paragraph("• <b>Receptive Field:</b> The specific region of the input image that directly influences the activation of a deeper neuron. Deeper layers aggregate larger spatial contexts.", bullet_style))
story.append(Paragraph("• <b>Pooling Layers:</b> Max-Pooling and Average-Pooling downsample spatial feature maps, providing minor spatial translation invariance and reducing memory consumption.", bullet_style))
story.append(Paragraph("• <b>Residual Networks (ResNets):</b> Introduced <b>Skip Connections (Identity Shortcuts)</b>: y = F(x, {W_i}) + x. By allowing gradients to flow unimpeded directly through the identity channel, ResNets resolved vanishing gradients and enabled training networks of 100+ layers.", bullet_style))

story.append(Paragraph("3.2 Recurrent Neural Networks (RNNs) & LSTMs for Temporal Sequences", h1_style))
story.append(Paragraph(
    "Standard RNNs model sequential data (text, time series) by maintaining an internal hidden state h_t updated at each discrete time step: h_t = tanh(W_hh · h_(t-1) + W_xh · x_t + b). However, backpropagation through time (BPTT) causes exponential gradient explosion or vanishing over long sequences.",
    body_style
))
story.append(Paragraph("<b>Long Short-Term Memory (LSTM) Networks</b> solve long-term temporal dependencies through an explicit Cell State C_t and three multiplicative gating mechanisms:", body_style))
story.append(Paragraph("• <b>Forget Gate:</b> f_t = σ(W_f · [h_(t-1), x_t] + b_f) determines what proportion of prior cell memory to discard.", bullet_style))
story.append(Paragraph("• <b>Input Gate & Candidate State:</b> i_t = σ(W_i · [h_(t-1), x_t] + b_i) and C̃_t = tanh(W_c · [h_(t-1), x_t] + b_c) decide which new candidate information to write to memory.", bullet_style))
story.append(Paragraph("• <b>Cell State Update:</b> C_t = f_t ⊙ C_(t-1) + i_t ⊙ C̃_t (linear additive gradient highway).", bullet_style))
story.append(Paragraph("• <b>Output Gate:</b> o_t = σ(W_o · [h_(t-1), x_t] + b_o); h_t = o_t ⊙ tanh(C_t) determines the new emitted hidden state.", bullet_style))

story.append(Paragraph("3.3 The Transformer & Self-Attention Mechanism", h1_style))
story.append(Paragraph(
    "Introduced in 'Attention Is All You Need' (Vaswani et al., 2017), the Transformer discarded sequential recurrence entirely in favor of parallelized Self-Attention mechanisms, powering modern generative AI:",
    body_style
))
story.append(Paragraph("• <b>Scaled Dot-Product Attention:</b> Projects each token embedding into Query (Q), Key (K), and Value (V) matrices:", body_style))
story.append(Paragraph("<b>Attention(Q, K, V) = softmax((Q · K^T) / sqrt(d_k)) · V</b>", body_style))
story.append(Paragraph("The scaling factor 1/sqrt(d_k) prevents dot products from growing excessively large in high dimensions, which would cause the softmax function to enter regions with minuscule gradients.", body_style))
story.append(Paragraph("• <b>Multi-Head Attention:</b> Computes h distinct attention projections in parallel, allowing the model to jointly attend to information from different representation subspaces (e.g., syntactic vs. semantic relationships).", bullet_style))
story.append(Paragraph("• <b>Positional Encoding:</b> Because self-attention is permutation-invariant, sinusoidal or rotary positional encodings (RoPE) are added to token embeddings to encode sequence order.", bullet_style))

story.append(Paragraph("3.4 Autoencoders, Encoders & Decoders (Unsupervised Representation Learning)", h1_style))
story.append(Paragraph(
    "An Autoencoder is an unsupervised neural network trained to reconstruct its input x at the output layer x̂ without labeled supervision, learning efficient compressed representations:",
    body_style
))
story.append(Paragraph("• <b>Encoder Network z = f_θ(x):</b> Compresses the high-dimensional input vector x into a low-dimensional latent space representation (bottleneck code z = σ(W_e · x + b_e)). The bottleneck forces the network to strip extraneous noise and preserve only the core, salient features.", bullet_style))
story.append(Paragraph("• <b>Decoder Network x̂ = g_ϕ(z):</b> Reconstructs an approximation of the original input from the compressed latent code (x̂ = σ(W_d · z + b_d)).", bullet_style))
story.append(Paragraph("• <b>Reconstruction Loss:</b> The model is trained end-to-end by minimizing reconstruction error: L(x, x̂) = ||x - x̂||² (Mean Squared Error) for continuous data or Binary Cross-Entropy for normalized inputs.", bullet_style))
story.append(Paragraph("• <b>Key Variants & Applications:</b> Denoising Autoencoders (DAEs) add artificial noise to inputs to learn robust features; Variational Autoencoders (VAEs) map inputs to a probabilistic latent distribution q(z|x) ~ N(μ, σ²) for generative modeling; Undercomplete Autoencoders provide non-linear dimensionality reduction superior to linear PCA.", bullet_style))

story.append(PageBreak())

# ==================== PAGE 4: Evaluation, Regularization & Modern Frontiers ====================
story.append(Paragraph("Unit 4: Model Evaluation, Optimization & Modern Frontiers", title_style))
story.append(Paragraph("Metrics, Normalization, Training Stability, and Foundation Models", subtitle_style))

story.append(Paragraph("4.1 Quantitative Model Evaluation Metrics", h1_style))
story.append(Paragraph("Relying solely on Accuracy is misleading for imbalanced datasets. Standard metrics derived from the Confusion Matrix (TP, FP, TN, FN) include:", body_style))
story.append(Paragraph("• <b>Precision = TP / (TP + FP):</b> Of all instances predicted positive, how many are truly positive? Critical when false alarms carry high costs (e.g., fraud flags).", bullet_style))
story.append(Paragraph("• <b>Recall (Sensitivity) = TP / (TP + FN):</b> Of all actual positive cases, how many did the model detect? Vital in medical triage and defect detection.", bullet_style))
story.append(Paragraph("• <b>F1-Score = 2 · (Precision · Recall) / (Precision + Recall):</b> The harmonic mean balancing precision and recall.", bullet_style))
story.append(Paragraph("• <b>ROC-AUC:</b> Area Under the Receiver Operating Characteristic Curve plots True Positive Rate vs. False Positive Rate across all classification thresholds, measuring rank-order separation power.", bullet_style))

story.append(Paragraph("4.2 Deep Network Normalization & Regularization Techniques", h1_style))
story.append(Paragraph("• <b>Batch Normalization (BatchNorm):</b> Normalizes activations across the mini-batch dimension: x̂ = (x - μ_B) / sqrt(σ_B² + ε), scaled and shifted by learnable parameters γ and β. Smooths the optimization landscape and enables higher learning rates.", bullet_style))
story.append(Paragraph("• <b>Layer Normalization (LayerNorm):</b> Normalizes across features for each individual sample independently: x̂ = (x - μ_L) / sqrt(σ_L² + ε). Essential for sequential and transformer models where batch sizes vary or are small.", bullet_style))
story.append(Paragraph("• <b>Dropout:</b> Randomly zeroes out a fraction p of hidden units during each forward training pass, preventing complex co-adaptations of feature detectors and acting as an implicit ensemble of 2^N sub-networks.", bullet_style))
story.append(Paragraph("• <b>Early Stopping & Learning Rate Schedules:</b> Monitoring validation loss to halt training before overfitting begins; pairing with Cosine Annealing or Warmup-Decay learning rate schedules for optimal convergence.", bullet_style))

story.append(Paragraph("4.3 Modern AI Frontiers: Foundation Models & RAG", h1_style))
story.append(Paragraph("• <b>Pre-training & Fine-Tuning Paradigm:</b> Modern models (LLMs like Llama, Grok, GPT) are pre-trained on massive corpora via self-supervised next-token prediction, followed by Reinforcement Learning from Human Feedback (RLHF) or DPO for alignment.", bullet_style))
story.append(Paragraph("• <b>Parameter-Efficient Fine-Tuning (PEFT / LoRA):</b> Low-Rank Adaptation (LoRA) freezes base model weights W_0 and injects trainable rank-decomposition matrices (W = W_0 + B · A, where r ≪ d), cutting trainable parameters by 99% while preserving performance.", bullet_style))
story.append(Paragraph("• <b>Retrieval-Augmented Generation (RAG):</b> Overcomes knowledge cutoff and hallucination by retrieving domain-specific text chunks via high-dimensional vector embeddings and cosine similarity search (pgvector), augmenting the LLM prompt with grounded context.", bullet_style))
story.append(Paragraph("• <b>AI Ethics & Responsible AI:</b> Detecting demographic bias in training corpora, mitigating model hallucination, ensuring explainability, and defending against adversarial prompt injections.", bullet_style))

doc.build(story)
print(f"Generated 4-page PDF successfully at: {output_pdf}")
