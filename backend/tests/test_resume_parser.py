
from unittest.mock import Mock, patch

import numpy as np

from app.schemas.resume import ResumeSchema
from app.services.resume_document_intelligence import (
    DocumentIntelligenceService,
)
from app.services.resume_embedding_service import (
    EmbeddingService,
)


@patch(
    "app.services.resume_document_intelligence.DocumentIntelligenceClient"
)
def test_extract_text(mock_client_class):
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_line_1 = Mock(content="John Doe")
    mock_line_2 = Mock(content="Python Developer")

    mock_page = Mock(
        lines=[mock_line_1, mock_line_2]
    )

    mock_result = Mock(
        pages=[mock_page]
    )

    mock_poller = Mock()
    mock_poller.result.return_value = mock_result

    mock_client.begin_analyze_document.return_value = (
        mock_poller
    )

    with patch.dict(
        "os.environ",
        {
            "AZURE_DOC_INTEL_ENDPOINT": "test-endpoint",
            "AZURE_DOC_INTEL_KEY": "test-key",
        },
    ):
        service = DocumentIntelligenceService()

        result = service.extract_text(
            b"fake-pdf-content"
        )

    assert result == "John Doe\nPython Developer\n"

    mock_client.begin_analyze_document.assert_called_once()


def create_resume():
    return ResumeSchema(
        professional_summary="A strong candidate.",
        skills={
            "technical": ["Python", "FastAPI"],
            "tools_and_technologies": ["Git"],
            "soft": ["Communication"],
        },
        experience=[
            {
                "job_title": "Developer",
                "company": "TestCo",
                "duration": "2 years",
                "years": 2,
                "responsibilities": ["Coding"],
                "technical_stack": ["Python"],
            }
        ],
        education=[
            {
                "degree": "BSc",
                "field": "Computer Science",
                "institution": "Uni",
                "graduation_year": 2020,
            }
        ],
        projects=[
            {
                "name": "Test Project",
                "description": "A project",
                "technical_stack": ["FastAPI"],
            }
        ],
        certifications=["Cert"],
        languages=["English"],
    )


def create_mock_model():
    mock_model = Mock()

    mock_model.max_seq_length = 384

    mock_model.tokenizer.encode.return_value = [
        1,
        2,
        3,
        4,
    ]

    mock_model.tokenizer.decode.return_value = (
        "Python FastAPI developer"
    )

    mock_model.encode.return_value = np.array(
        [[0.1, 0.2, 0.3]]
    )

    return mock_model


def test_build_semantic_sections_includes_semantic_sections():
    resume = create_resume()

    with patch(
        "app.services.resume_embedding_service.SentenceTransformer"
    ):
        service = EmbeddingService()

    sections = service.build_semantic_sections(resume)

    assert "professional_summary" in sections
    assert "skills" in sections
    assert "experience" in sections
    assert "projects" in sections

    assert "education" not in sections
    assert "certifications" not in sections
    assert "languages" not in sections

    assert "A strong candidate." in sections[
        "professional_summary"
    ]

    assert "Python" in sections["skills"]
    assert "FastAPI" in sections["skills"]
    assert "Git" in sections["skills"]
    assert "Communication" in sections["skills"]

    assert "Developer" in sections["experience"]
    assert "TestCo" in sections["experience"]
    assert "Coding" in sections["experience"]

    assert "Test Project" in sections["projects"]
    assert "A project" in sections["projects"]
    assert "FastAPI" in sections["projects"]


def test_build_hard_requirements_keeps_structured_data():
    resume = create_resume()

    with patch(
        "app.services.resume_embedding_service.SentenceTransformer"
    ):
        service = EmbeddingService()

    requirements = service.build_hard_requirements(
        resume
    )

    assert requirements["location"] == ""

    assert requirements["experience"] == resume.experience
    assert requirements["education"] == resume.education
    assert requirements["certifications"] == [
        "Cert"
    ]
    assert requirements["languages"] == [
        "English"
    ]


def test_generate_embedding_returns_normalized_list():
    mock_model = create_mock_model()

    with patch(
        "app.services.resume_embedding_service.SentenceTransformer",
        return_value=mock_model,
    ):
        service = EmbeddingService()

    embedding = service.generate_embedding(
        "Python FastAPI developer"
    )

    assert isinstance(embedding, list)
    assert len(embedding) == 3

    assert all(
        isinstance(value, float)
        for value in embedding
    )

    expected = np.array([0.1, 0.2, 0.3])
    expected = expected / np.linalg.norm(expected)

    np.testing.assert_allclose(
        embedding,
        expected.tolist(),
    )

    mock_model.tokenizer.encode.assert_called_once_with(
        "Python FastAPI developer",
        add_special_tokens=False,
    )

    mock_model.tokenizer.decode.assert_called_once_with(
        [1, 2, 3, 4],
        skip_special_tokens=True,
    )

    mock_model.encode.assert_called_once_with(
        ["Python FastAPI developer"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


def test_generate_embedding_returns_empty_list_for_empty_text():
    mock_model = create_mock_model()

    mock_model.tokenizer.encode.return_value = []

    with patch(
        "app.services.resume_embedding_service.SentenceTransformer",
        return_value=mock_model,
    ):
        service = EmbeddingService()

    embedding = service.generate_embedding("")

    assert embedding == []

    mock_model.encode.assert_not_called()


def test_generate_resume_embeddings_generates_embedding_per_section():
    mock_model = create_mock_model()

    mock_model.encode.side_effect = [
        np.array([[0.1, 0.2, 0.3]]),
        np.array([[0.4, 0.5, 0.6]]),
    ]

    resume = create_resume()

    with patch(
        "app.services.resume_embedding_service.SentenceTransformer",
        return_value=mock_model,
    ):
        service = EmbeddingService()

    with patch.object(
        service,
        "build_semantic_sections",
        return_value={
            "professional_summary": "A strong candidate.",
            "skills": "Python FastAPI Git Communication",
        },
    ):
        embeddings = service.generate_resume_embeddings(
            resume
        )

    assert isinstance(embeddings, dict)

    assert set(embeddings.keys()) == {
        "professional_summary",
        "skills",
    }

    assert len(
        embeddings["professional_summary"]
    ) == 3

    assert len(
        embeddings["skills"]
    ) == 3

    assert all(
        isinstance(value, float)
        for embedding in embeddings.values()
        for value in embedding
    )

    assert mock_model.encode.call_count == 2

