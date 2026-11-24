=== 10 道 FlashAttention 单选题（材料）===

Q1. According to the course summary of the FlashAttention teaching kernel, what is the core algorithmic idea? [ref_2]
   A. Tiled GEMM + Online Softmax
   B. Sparse attention + pruning
   C. Low-rank approximation of Q and K
   D. Quantizing Q, K and V to INT8
   正确答案: Tiled GEMM + Online Softmax
   错误回答(用于测试): Sparse attention + pruning

Q2. Which two intermediate tensors does FlashAttention avoid writing to global memory in full? [ref_2]
   A. S = QK^T and P = softmax(S)
   B. Q and K
   C. V and the output O
   D. The running maximum m and the running normalizer l
   正确答案: S = QK^T and P = softmax(S)
   错误回答(用于测试): Q and K

Q3. In the FlashAttention loop over key/value tiles, which quantities are carried along as running state? [ref_2]
   A. A running maximum m and a running normalizer l
   B. The full score matrix S
   C. A copy of every previous tile of K
   D. The gradient of the loss with respect to Q
   正确答案: A running maximum m and a running normalizer l
   错误回答(用于测试): The full score matrix S

Q4. What does the course list as the fused kernel structure that real FlashAttention-1 adds? [ref_2]
   A. QK^T -> online softmax -> PV in one fused kernel
   B. QK^T -> write S to global memory -> separate softmax kernel -> PV
   C. softmax -> QK^T -> PV
   D. PV -> online softmax -> QK^T
   正确答案: QK^T -> online softmax -> PV in one fused kernel
   错误回答(用于测试): QK^T -> write S to global memory -> separate softmax kernel -> PV

Q5. In the shared-memory tiled GEMM kernel, what is the purpose of the two __syncthreads() calls around the inner compute loop? [ref_17]
   A. The first waits until the whole tile has been loaded into shared memory; the second ensures all threads finish using the tile before the next tile overwrites it
   B. They synchronize the GPU with the host CPU
   C. They allocate the shared-memory arrays As and Bs
   D. They perform the reduction of the sum across threads
   正确答案: The first waits until the whole tile has been loaded into shared memory; the second ensures all threads finish using the tile before the next tile overwrites it
   错误回答(用于测试): They synchronize the GPU with the host CPU

Q6. In the tiled GEMM kernel, the outer loop advances with 'for (int t = 0; t < (N + TILE_SIZE - 1) / TILE_SIZE; t++)'. What does this loop iterate over? [ref_17]
   A. Tiles along the K (reduction) dimension, accumulating into a single scalar sum
   B. Tiles along the output row dimension, writing one row per iteration
   C. The batch dimension of the input matrices
   D. The number of CUDA blocks launched
   正确答案: Tiles along the K (reduction) dimension, accumulating into a single scalar sum
   错误回答(用于测试): Tiles along the output row dimension, writing one row per iteration

Q7. Why does the plain softmax sum exp(x_j) overflow for an input such as x = (1000, 1001, 1002)? [ref_15]
   A. Because exp(1000) is about 1.97e434, which exceeds the maximum representable float64 value of about 1.8e308
   B. Because the input vector has more than two elements
   C. Because the denominator is computed in integer arithmetic
   D. Because softmax requires the inputs to be sorted first
   正确答案: Because exp(1000) is about 1.97e434, which exceeds the maximum representable float64 value of about 1.8e308
   错误回答(用于测试): Because the input vector has more than two elements

Q8. In the stable softmax derivation, the shift constant is chosen as c = m = max_j(x_j). Which statement best explains why this choice is made? [ref_13]
   A. It prevents overflow because exp(x_j - c) <= 1, and it avoids catastrophic underflow because the largest shifted term becomes exactly 0 in the exponent
   B. It makes the output values sum to a value larger than one
   C. It removes the need to divide by the denominator
   D. It guarantees the output is exactly uniform
   正确答案: It prevents overflow because exp(x_j - c) <= 1, and it avoids catastrophic underflow because the largest shifted term becomes exactly 0 in the exponent
   错误回答(用于测试): It makes the output values sum to a value larger than one

Q9. In the online softmax recurrence, the normalizer is updated as d = d * expf(m - m_new) + expf(input[j] - m_new). What is the role of the factor expf(m - m_new)? [ref_8]
   A. It rescales the previously accumulated normalizer from the old maximum m to the new maximum m_new
   B. It normalizes the final output to sum to one
   C. It computes the running maximum itself
   D. It is a numerical guard against division by zero
   正确答案: It rescales the previously accumulated normalizer from the old maximum m to the new maximum m_new
   错误回答(用于测试): It normalizes the final output to sum to one

Q10. The course defines the online softmax state with m_{j-1} = max over 1<=i<=j-1 of x_i and d-hat_{j-1} = sum_{i=1}^{j-1} e^{x_i - m_{j-1}}. What is the key advantage of this formulation over the two-pass stable softmax? [ref_9]
   A. The maximum and the normalizer are updated together in a single streaming pass, so the input does not need to be read twice
   B. It produces a different mathematical result from the two-pass version
   C. It eliminates the need for any exponentiation
   D. It requires storing the entire input vector in shared memory
   正确答案: The maximum and the normalizer are updated together in a single streaming pass, so the input does not need to be read twice
   错误回答(用于测试): It produces a different mathematical result from the two-pass version
