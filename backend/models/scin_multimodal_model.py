"""
Google SCIN Multimodal Neural Network Architecture
Pairs a deep vision backbone (ResNet / EfficientNet) with a tabular symptom MLP
for multi-label skin condition diagnosis and fairness-aware screening.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


class TabularSymptomEncoder(nn.Module):
    """
    Multi-Layer Perceptron (MLP) for encoding structured clinical symptoms,
    anatomical locations, lesion duration, and demographic context.
    """

    def __init__(self, input_dim: int = 58, hidden_dim: int = 256, embed_dim: int = 128, dropout: float = 0.3):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class VisionBackbone(nn.Module):
    """
    Vision encoder based on pretrained ResNet34 extracting 512-dim spatial features.
    """

    def __init__(self, embed_dim: int = 512, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()
        weights = models.ResNet34_Weights.DEFAULT if pretrained else None
        resnet = models.resnet34(weights=weights)

        # Remove the final 1000-class FC layer
        in_features = resnet.fc.in_features
        resnet.fc = nn.Identity()
        self.backbone = resnet

        self.projection = nn.Sequential(
            nn.Linear(in_features, embed_dim),
            nn.BatchNorm1d(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        return self.projection(feat)


class SCINMultimodalModel(nn.Module):
    """
    Full Multimodal Skin Condition Classifier.
    Fuses vision features and structured clinical symptom features.
    """

    def __init__(
        self,
        num_classes: int = 20,
        tabular_dim: int = 58,
        image_embed_dim: int = 512,
        tabular_embed_dim: int = 128,
        fusion_hidden_dim: int = 256,
        dropout: float = 0.3,
        pretrained_vision: bool = True,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.vision_encoder = VisionBackbone(embed_dim=image_embed_dim, pretrained=pretrained_vision, dropout=dropout)
        self.symptom_encoder = TabularSymptomEncoder(input_dim=tabular_dim, hidden_dim=256, embed_dim=tabular_embed_dim, dropout=dropout)

        total_embed_dim = image_embed_dim + tabular_embed_dim

        # Multimodal Fusion Head
        self.fusion_head = nn.Sequential(
            nn.Linear(total_embed_dim, fusion_hidden_dim),
            nn.LayerNorm(fusion_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden_dim, num_classes),
        )

        # Standalone Heads for Image-only and Tabular-only inference/ablation
        self.image_only_head = nn.Sequential(
            nn.Linear(image_embed_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )
        self.tabular_only_head = nn.Sequential(
            nn.Linear(tabular_embed_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(
        self,
        images: torch.Tensor = None,
        tabular: torch.Tensor = None,
        mode: str = "multimodal",
    ) -> torch.Tensor:
        """
        Forward pass.
        mode: 'multimodal', 'image_only', or 'tabular_only'.
        Returns unnormalized logits of shape (batch_size, num_classes).
        """
        if mode == "image_only" or (images is not None and tabular is None):
            img_emb = self.vision_encoder(images)
            return self.image_only_head(img_emb)

        if mode == "tabular_only" or (tabular is not None and images is None):
            tab_emb = self.symptom_encoder(tabular)
            return self.tabular_only_head(tab_emb)

        # Full Multimodal
        img_emb = self.vision_encoder(images)
        tab_emb = self.symptom_encoder(tabular)

        fused = torch.cat([img_emb, tab_emb], dim=1)
        logits = self.fusion_head(fused)
        return logits

    def predict_proba(
        self,
        images: torch.Tensor = None,
        tabular: torch.Tensor = None,
        mode: str = "multimodal",
    ) -> torch.Tensor:
        """Computes multi-label probabilities using Sigmoid."""
        logits = self.forward(images=images, tabular=tabular, mode=mode)
        return torch.sigmoid(logits)
