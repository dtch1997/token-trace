from functools import partial
from typing import cast

import pytest
import torch
from sae_lens import SparseAutoencoder
from sae_lens.toolkit.pretrained_saes import get_gpt2_res_jb_saes
from token_trace.sae_circuit import (
    MetricFunction,
    ModuleName,
    dense_to_sparse,
    get_sae_cache_dict,
    last_token_loss,
)
from transformer_lens import HookedTransformer

# device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
device = torch.device("cpu")


@pytest.fixture(scope="module")
def model() -> HookedTransformer:
    return cast(HookedTransformer, HookedTransformer.from_pretrained("gpt2").to(device))


@pytest.fixture(scope="module")
def sae_dict() -> dict[ModuleName, SparseAutoencoder]:
    sae_dict = get_gpt2_res_jb_saes()[0]
    sae_dict = {ModuleName(k): v.to(device) for k, v in sae_dict.items()}
    return sae_dict


@pytest.fixture(scope="module")
def prompt() -> str:
    return "Hello world"


def test_dense_to_sparse_device():
    dense_tensor = torch.tensor([[3, 0, 0], [0, 4, 5], [0, 0, 0]], device=device)
    sparse_tensor = dense_to_sparse(dense_tensor)
    assert sparse_tensor.device.type == device.type


def test_dense_to_sparse_dim_2():
    dense_tensor = torch.tensor([[3, 0, 0], [0, 4, 5], [0, 0, 0]])
    sparse_tensor = dense_to_sparse(dense_tensor)
    dense_reconstructed = sparse_tensor.to_dense()
    assert torch.allclose(dense_tensor, dense_reconstructed)


def test_dense_to_sparse_dim_3():
    dense_tensor = torch.tensor(
        [
            [[0, 0, 0], [0, 8, 0], [0, 0, 0]],
            [[5, 0, 0], [0, 0, 7], [0, 0, 0]],
            [[0, 0, 0], [0, 0, 0], [0, 6, 0]],
        ]
    )
    sparse_tensor = dense_to_sparse(dense_tensor)
    dense_reconstructed = sparse_tensor.to_dense()
    assert torch.allclose(dense_tensor, dense_reconstructed)


def test_get_sae_cache_dict(
    model: HookedTransformer, sae_dict: dict[ModuleName, SparseAutoencoder], prompt: str
):
    metric_fn: MetricFunction = partial(last_token_loss, prompt=prompt)

    sae_cache_dict = get_sae_cache_dict(
        model=model,
        sae_dict=sae_dict,
        metric_fn=metric_fn,
    )

    for name, module_activations in sae_cache_dict.items():
        assert module_activations.module_name == name
        assert module_activations.activations is not None
        assert module_activations.gradients is not None
