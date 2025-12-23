"""Utilities to process raw job postings extracted from LinkedIn.

This module provides the `LinkedInDataPipeline` class which helps cleaning,
normalizing and extracting structured information from job descriptions.
It uses regular expressions for fast detection and offers hooks for LLM
fallbacks via `transformers.pipeline` when necessary.

Example usage:

    from data_treatment.likedin_data_pipeline import LinkedInDataPipeline

    pipeline = LinkedInDataPipeline("data/linkedin_data_raw.json")
    pipeline.run_pipeline("out/cleaned_jobs.csv")

Documentation and typing follow PEP 257 / PEP 484.
"""

from typing import Any, Callable, Dict, List, Optional

import re
import unicodedata
import pandas as pd
import torch.cuda as cuda
from transformers import pipeline
import json
from tqdm import tqdm

REGIONS_REGEX: Dict[str, str] = {
    "MG": r"\b(minas\s*gerais|mg)\b",
    "SP": r"\b(s[ãa]o\s*paulo|sp)\b",
    "RJ": r"\b(rio\s*de\s*janeiro|rio|rj)\b",
    "DF": r"\b(distrito\s*federal|df|brasilia|bras[íi]lia)\b",
    "RS": r"\b(rio\s*grande\s*do\s*sul|rs)\b",
    "PR": r"\b(paran[áa]|pr)\b",
    "SC": r"\b(santa\s*catarina|sc)\b",
    "BA": r"\b(bahia|ba)\b",
    "PE": r"\b(pernambuco|pe)\b",
    "CE": r"\b(cear[áa]|ce)\b",
    "GO": r"\b(goi[áa]s|go)\b",
    "ES": r"\b(esp[íi]rito\s*santo|es)\b",
    "AM": r"\b(amazona[as]|am)\b",
    "PA": r"\b(par[áa]|pa)\b",
    "MA": r"\b(maranh[ãa]o|ma)\b",
    "RN": r"\b(rio\s*grande\s*do\s*norte|rn)\b",
    "PB": r"\b(para[íi]ba|pb)\b",
    "PI": r"\b(piau[íi]|pi)\b",
    "AL": r"\b(alagoas|al)\b",
    "SE": r"\b(sergipe|se)\b",
    "MT": r"\b(mato\s*grosso|mt)\b",
    "MS": r"\b(mato\s*grossso\s*do\s*sul|ms)\b",
    "RO": r"\b(rond[ôo]nia|ro)\b",
    "AC": r"\b(acre|ac)\b",
    "AP": r"\b(amap[áa]|ap)\b",
    "RR": r"\b(roraima|rr)\b",
    "TO": r"\b(tocantins|to)\b",
    "BR": r"\b(brasil|brazil|br)\b",
    "REMOTE": r"\b(remote|remoto|home\s*office|homeoffice|trabajo\s*desde\s*casa|work\s*from\s*home|wfh|100%\s*remoto|totalmente\s*remoto|full\s*remote|fully\s*remote)\b"
}
SENIORITY_REGEX: Dict[str, str] = {
    "estagio": r"\b(estagio|estagiari[oa]|intern(?:ship)?|trainee|aprendiz|jovem aprendiz|young\s*guns|early\s*career|programa\s+acelera|bolsista)\b",
    "junior": r"\b(jr\.?|junior|entry\s*level|entry|associate|nivel\s*1|n1|l1|nivel\s+inicial|iniciante|auxiliar|associado)\b",
    "pleno": r"\b(pl\.?|pleno|mid(?:\s*level)?|middle|intermediate|nivel\s*2|n2|l2)\b",
    "staff": r"\b(staff|principal|distinguished|specialist\s+principal)\b",
    "senior": r"\b(sr\.?|senior|senioridade|sennior|nivel\s*3|n3|l3|expert|especialista\b|especialista\s+seni(?:or)?|specialist|executivo)\b",
    "lead": r"\b(lead|tech\s*lead|team\s*lead|lider|lideranca|lider\s+tecnico|coordenador\s+tecnico|lider\s+de\s+projetos|lider\s+de\s+equipe|lider\s+tecnico|tech\s+manager|team\s+leader)\b",
    "manager": r"\b(manager|gerente|head|coordenador(?:a)?|coord\.?|supervisor(?:a)?|director|diretor(?:a)?|vp|vice\s*president|v\.?p\.?|cto|ceo|cfo|cpo|cio|chief|c\s*level|executive|managing\s+director|country\s+manager)\b",

}

ROLE_REGEX: Dict[str, str] = {
    "data_scientist": r"\b(data\s*scientist|data\s*science|cientista\s+de\s+dados|cientista\s+dados|research\s+scientist|ciencia\s+de\s+datos?|cientifico\s+de\s+datos)\b",
    "machine_learning_engineer": r"\b(machine\s*learning\s*engineer|ml\s*engineer|mle|machine\s*learning|mlops|ml\s*ops|m\s*l\s*ops|machine\s+leaning\s+engineer|llm\s+training)\b",
    "ai_engineer": r"\b(ai\s*engineer|ia\s*engineer|engenheir[oa]\s+de\s+ia|artificial\s+intelligence\s*engineer|ai\s*trainer|ai\s+solutions\s+engineer|ai\s+automation\s+engineer)\b",
    "ai_general": r"\b(generative\s*ai|gen\s*ai|genai|artificial\s+intelligence|inteligencia\s+artificial|\bai\b|\bia\b|learnwith\.ai)\b",
    "data_engineer": r"\b(data\s*engineer|engenheir[oa]\s+de\s+dados|engenheir[oa].*dados|engenharia\s+de\s+dados|big\s*data|data\s*platform(?:\s*engineer)?|etl\b|elt\b|pipeline\b|spark\b|airflow\b|databricks\b|kafka\b|hadoop\b|dataops\b|etl\s*developer|data\s*enginner|data\s+integration\s+engineer|data\s+lead\s+engineer|snowflake|data\s+transformation|data\s+engineering|data\s+modeler)\b",
    "analytics_engineer": r"\b(analytics\s*engineer|analytics\s*engineering|analytics\s*eng|dbt\b|analyst\s*engineering|engenheiro\s*a?\s*de\s+analytics|web\s+analytics|data\s+analytics)\b",
    "data_analyst": r"\b(data\s*analyst|analista\s+de\s+dados|business\s*intelligence|business\s+inteligence|\bbi\b|analista\b|analyst\b|reporting\b|tableau\b|power\s*bi|powerbi\b|qlik\b|looker\b|business\s+analyst|modelagem|market\s+insights|fraud\s+data|analt\b)\b",

    "cloud_engineer": r"\b(cloud\s*engineer|aws\s*engineer|gcp\s*engineer|azure\s*engineer|cloud\s+specialist|engenheiro\s+cloud)\b",
    "system_engineer": r"\b(system\s*engineer|systems\s*engineer|engenheiro\s+de\s+sistemas?|engenheiro\s+sistema)\b",
    "devops": r"\b(devops|sre|site\s*reliability|infra(?:structure)?|platform\s*engineer|plataforma|engenheiro\s+de\s+infraestrutura)\b",
    "qa": r"\b(qa|quality\s*assurance|tester|testes|quality\s*engineer|software\s+test\s+engineer|code\s+reviewer)\b",
    "architect": r"\b(architect|arquit(?:et[oa]|eto|eta)|arquitetura|software\s+architecture)\b",
    "software_engineer": r"\b(software\s*engineer|software\s*developer|engenheir[oa]\s+de\s+software|desenvolvedor\s+de\s+software|software\s+development|ingeniero\s+de\s+software|desarrollo\s+de\s+software|software\s+engineering|engenheiro\s*a?\s+de\s+software)\b",
    "backend_engineer": r"\b(back\s*end|backend|api\b|python\s*developer|node\b|nodejs\b|golang\b|java\s*developer|dotnet|\.net|csharp|c#|php\b|ruby\b|desenvolvedor\s+python|desenvolvedor\s+java|programador|sql\b|aem\b|desenvolvimento\s+java|javascript)\b",
    "frontend_engineer": r"\b(front\s*end|frontend|react\b|angular\b|vue\b|frontend\s*developer|desarrollador\s+web)\b",
    "fullstack_engineer": r"\b(full\s*stack|fullstack)\b",
    "mobile_engineer": r"\b(mobile\s*engineer|android\s*engineer|ios\s*engineer|mobile\s*developer|desenvolvimento\s+mobile|kotlin\b|swift\b|flutter\b|react\s*native|mobile\b)\b",
    "developer": r"\b(developer|desenvolvedor(?:a)?|dev\b|desarrollador)\b",
    "solutions_engineer": r"\b(solutions?\s*engineer|engenheiro\s+de\s+solucoes?|solution\s+engineer|gtm\s+engineer|partner\s+engineer|forward\s+deployed\s+engineer)\b",
    "integration_engineer": r"\b(integration\s*engineer|engenheiro\s+de\s+integracao)\b",
    "engineer_general": r"\b(engineer|engenheiro(?:a)?)\b",

    "scrum_master": r"\b(scrum\s*master|agilista|agile\s*coach)\b",
    "product_manager": r"\b(product\s*manager|product\s*owner|\bpm\b|gerente\s+de\s+produtos?|gestao\s+de\s+produtos?|product)\b",
    "project_manager": r"\b(project\s*manager|gerente\s+de\s+projetos?|pmo\b|project\s*management|gerente\s+de\s+portfolio|strategic\s+projects)\b",
    "engineering_manager": r"\b(engineering\s*manager|gerente\s+de\s+engenharia|gerente\s+de\s+tecnologia|tecnologia\s+gerente)\b",
    "business_manager": r"\b(gerente\s+de\s+neg(?:ocios?)?|gerente\s+de\s+servicos|business\s+partner|negocios\s+e\s+servicos|gerente\s+de\s+relacionamento|relacionamento)\b",
    "account_manager": r"\b(account\s*manager|key\s*account|account\s*director|gerente\s+de\s+conta[s]?|agency\s+manager|client\s+advisor|executivo\s+de\s+contas)\b",
    "talent_manager": r"\b(talent\s*manager|gerente\s+de\s+talentos|organizational\s+effectiveness)\b",
    "customer_success": r"\b(customer\s*success|gerente\s+de\s+sucesso|sucesso\s+do\s+cliente|customer\s+experience|cx\b|customer\s+service|ouvidoria|partner\s+success|voice\s+of\s+customer|voc\b)\b",
    "marketing": r"\b(marketing|growth|seo\b|ads\b|midia|media\b|performance|public\s+relations|communications?\s+partner|community\s+engagement|campaigns|shopper\s+insights|visual\s+merchandising|pr\s+manager)\b",
    "sales": r"\b(sdr\b|sales|vendas|account\s*executive|closer|bd\b|bdr\b|business\s*development|comercial|representante|vendedor|inside\s*sales|appointment\s+setter|etf\s+distribution|renewals\s+manager)\b",
    "operations": r"\b(operations|operacoes|logistica|supply\s*chain|operational\s+excellence|continuous\s+improvement|scheduling\s+optimization|excelencia\s+operacional|transformation\s+office|process\s+optimization|desenvolvimento\s+de\s+processos)\b",
    "finance": r"\b(finance|financas|fp\s*&\s*a|fpa\b|credit|risk|control(?:lership)?|compensation|bookkeeper|anti\s+money\s+laundering|pld\b|banking|tax\b|assessor\s+de\s+investimentos|investimentos|asset\s+management|payments)\b",
    "hr": r"\b(hr\b|human\s*resources|recruiter|recrutador(?:a)?|reclutador|talent\s*acquisition|people\b|rh\b|recrutamento|selecao|pessoal|headhunter|pessoas\s+e\s+cultura|treinamento\s+e\s+desenvolvimento|cultura\s+e\s+comunicacao|recruiting|sourcer)\b",
    "fraud": r"\b(fraud\s*(?:strategy)?|fraude|prevencao\s+a?\s+fraude|investigations?)\b",
    "government_relations": r"\b(government\s*relations|relacoes\s+governamentais|law\s+enforcement)\b",

    "administrator": r"\b(administrator|administrador(?:a)?|administrativo(?:a)?|admin\b|servicos\s+administrativos)\b",
    "assistant": r"\b(assistant|assistente|executive\s*assistant|assistente\s+executivo|assistente\s+pessoal)\b",
    "coordinator": r"\b(coordinator|coordenador(?:a)?|coordenacao|coord\b)\b",
    "specialist": r"\b(specialist|especialista|espec\b|esp\b)\b",
    "support": r"\b(support|suporte|customer\s*support|atendimento|customer\s*care|help\s*desk|service\s*desk|analista\s+de\s+suporte|suporte\s+ao\s+cliente)\b",
    "receptionist": r"\b(recepcionista|receptionist|secretaria)\b",
    "dispatcher": r"\b(despachante|dispatcher)\b",

    "research": r"\b(research|pesquisa|pesquisador(?:a)?|doutor|neurohub)\b",
    "consultant": r"\b(consultant|consultor(?:a)?|cons\b)\b",
    "annotator": r"\b(annotator|annotation|anotador|anotacao|avaliador|transcription|audio\s*data|internet\s+assessor|personalized\s+internet|audio\s+personalization\s+evaluator|voice\s+coach)\b",
    "data_collector": r"\b(data\s*collector|coletor(?:a)?\s+de\s+dados)\b",
    "video_editor": r"\b(video\s*editor|editor(?:a)?\s+de\s+video|videomaker|criador(?:a)?\s+de\s+conteudo|content\s*creator|video\s+production|criacao\s+com\s+ia)\b",
    "librarian": r"\b(bibliotecari[oa]|curador)\b",
    "talent_pool": r"\b(banco\s+de\s+talentos?|talent\s*pool|banco\s+de\s+candidaturas?|indique\s+ou\s+candidate|mentes\s+brilhantes|careers\s+in\s+brazil|junte\s+se\s+ao\s+nosso|deixe\s+seu\s+curriculo|nosso\s+radar|kunumi)\b",
    "job_code": r"\b\d{3,}\b",
    "intern": r"\b(estagio|estagiari[oa]|intern(?:ship)?|trainee|aprendiz)\b",
    "legal": r"\b(legal|juridico|advogado|counsel|lawyer|paralegal|policy)\b",
    "security": r"\b(security|seguranca|cyber|ciber|infosec|red\s+team|ehs\b)\b",
    "education": r"\b(tutor|professor|teacher|instructor|instrutor|educador|pedagog[oa]|e\s*commerce\s+educacional|ensino)\b",
    "writer": r"\b(writer|redator|copywriter|copyeditor|content|conteudo|jornalista|content\s+writer|editor|linguist)\b",
    "design": r"\b(design|designer|ux|ui|web\s*design|graphic|art\s*director|diretor\s+de\s+arte|digital\s+experience)\b",
    "data_entry": r"\b(data\s*entry|digitador)\b",
    "translator": r"\b(translator|tradutor|interpreter|interprete|localization)\b",
    "healthcare": r"\b(nurse|enfermeir[oa]|medico|doctor|psychologist|psicolog[oa]|saude|health|beauty\s+advisor|nutricao)\b",
    "reporter": r"\b(reporter|jornalista|sports\s+reporter)\b",
    "game_presenter": r"\b(game\s+presenter[s]?|apresentador|relocation\s+to\s+armenia)\b",
    "freelance": r"\b(freelance|freelancer|prestador\s+de\s+servicos?|pj\b|autonomo)\b",
    "general": r"\b(generalist|generalista|startup\s+generalist|founder)\b",
    "e_commerce": r"\b(e\s*commerce|ecommerce|marketplace|digital|omnicanal)\b",
    "innovation": r"\b(innovation|inovacao|new\s+ventures)\b",
    "partnerships": r"\b(partnerships?|parcerias)\b",
    "salesforce": r"\b(salesforce)\b",
    "rpg_developer": r"\b(rpg\s*as\s*set|rpg\b)\b",
    "geospatial": r"\b(photogrammetry|gis\b|geospatial|survey)\b",
    "ti_general": r"\b(ti\b|tecnologia\s+da\s+informacao|it\b|information\s+technology)\b",
    "chatbot": r"\b(chatbot|bot\b|conversational)\b",
    "renewables": r"\b(renewables|energia\s+renovavel|sustentabilidade|sustainability)\b",
    "real_estate": r"\b(lease|property|imoveis|real\s+estate)\b",
    "link_builder": r"\b(link\s+builder)\b"
}

class LinkedInDataPipeline:
    """Class for processing and extracting job posting data from LinkedIn.

    The class loads a JSON file with raw records (expected to be compatible
    with `pandas.read_json`) and provides methods to:
    - normalize text fields
    - identify seniority and role via regex (with optional LLM fallback)
    - detect region
    - extract structured fields using regex or an LLM

    Args:
        raw_data_path: Path to the JSON file containing raw LinkedIn data.

    Attributes:
        df: DataFrame with loaded data and extra columns created by methods.
        _title_generator: Lazy-loaded pipeline used for title/LLM generation.
    """

    def __init__(self, raw_data_path: str) -> None:
        self.raw_data_path: str = raw_data_path
        self.df: pd.DataFrame = pd.read_json(self.raw_data_path)
        self._title_generator: Optional[Callable[..., Any]] = None

    def clean_job_raw_positions(self, column: str = "raw_position", fallback_to_llm: bool = False) -> None:
        """Detect `seniority` and `role` from the raw position/title column.

        The method normalizes the `column` and `raw_html_description` (creating
        `normalized_{column}` and `normalized_raw_html_description`) and attempts
        to map the position to keys defined in `SENIORITY_REGEX` and `ROLE_REGEX`.

        If `fallback_to_llm` is True and no match is found, `_generate_title`
        will be used as a fallback to suggest a title via an LLM. If the LLM
        fails the resulting field will be set to an empty string.

        Args:
            column: Name of the column with the raw title/position (default: "raw_position").
            fallback_to_llm: If True, allow LLM fallback for unmapped titles.
        """
        self.normalize_text(column)
        self.normalize_text("raw_html_description")

        def _first_match(text: str, description: str, patterns: Dict[str, str]) -> str:
            for key, pat in patterns.items():
                if re.search(pat, text):
                    return key
            if not fallback_to_llm:
                return text
            # Fallback to LLM generation if no match found
            generated_title = self._generate_title(text, description)
            if generated_title and (generated_title not in patterns.keys()):
                print(f"Generated title '{generated_title}' for the {text} not in known roles.")
            else:
                print(f"LLM generated title: {generated_title} for text: {text}")
            return generated_title or ""

        col = f"normalized_{column}"
        if col not in self.df:
            return

        self.df["seniority"] = self.df.apply(
            lambda row: _first_match(row[col], row.get("normalized_raw_html_description", ""), SENIORITY_REGEX),
            axis=1,
        )
        self.df["role"] = self.df.apply(
            lambda row: _first_match(row[col], row.get("normalized_raw_html_description", ""), ROLE_REGEX),
            axis=1,
        )


    def normalize_text(self, column: str) -> None:
        """Normalize text by removing accents, converting to lowercase and
        replacing common punctuation characters with spaces.

        The result is stored in a new column named `normalized_{column}`.

        Args:
            column: Name of the column to normalize.
        """
        texts = self.df[column].astype(str)

        def normalize(text: str) -> str:
            text = text.lower()
            text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
            text = re.sub(r"[\(\)\[\]\|\-–—_/]", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text

        self.df[f"normalized_{column}"] = texts.apply(normalize)

    def save_cleaned_data(self, output_path: str) -> None:
        """Save the cleaned DataFrame to CSV.

        Args:
            output_path: Path of the output CSV file.
        """
        self.df.to_csv(output_path, index=False)
    
    def clan_regions(self, column: str = "raw_location") -> None:
        """Detect region/state from a free-form location column.

        Uses `REGIONS_REGEX` for fast detection. If no match is found and an
        LLM generator is available, the method will prompt the LLM to try to
        identify the region.

        Args:
            column: Name of the column that contains location text (default: "raw_location").
        """
        self.normalize_text(column)

        def _first_region(text: str) -> str:
            for key, pat in REGIONS_REGEX.items():
                if re.search(pat, text):
                    return key

            if not self._title_generator:
                generator = self._load_title_generator()
            else:
                generator = self._title_generator

            prompt = (
                "Task: Identify location or region mentioned in the text below.\n"
                "Rules:\n"
                "- If multiple states or regions are mentioned, choose the most relevant one.\n"
                "- If no state, region or remote modality is mentioned, respond with 'no information'.\n"
                "- Respond with only the state abbreviation or region name.\n"
                "- If Remote modality is mentioned, return 'remote'.\n\n"
                f"Text: {text}\n\n"
                "Answer:"
            )

            try:
                result = generator(prompt)
            except Exception:
                return ""
            if not result:
                return ""

            print("LLM generated region:", result, "for the following text: \n", text)
            print("---")
            return str(result[0].get("generated_text", "")).strip()

        col = f"normalized_{column}"
        if col not in self.df:
            return
        self.df["region"] = self.df[col].apply(_first_region)

    def extract_information(
        self,
        cols: List[str] = [
            "benefits",
            "salary",
            "requirements",
            "technologies",
            "contract_type",
            "work_model",
            "experience_years",
            "education",
            "languages",
            "company_size",
        ],
        description_col_name: str = "raw_html_description",
        llm_name: str = "google/flan-t5-base",
        batch_size: int = 4,
        max_tokens: int = 128,
    ) -> None:
        """Extract structured fields from job descriptions using an LLM.

        For each field in `cols`, a short prompt is built for the `llm_name`
        model and `transformers.pipeline` is used to generate answers.

        Args:
            cols: List of fields to extract (e.g. ["benefits", "salary"]).
            description_col_name: Column name that contains the job description.
            llm_name: Transformers model identifier to use for extraction.
            batch_size: Batch size for LLM calls.
            max_tokens: Maximum new tokens generated per response.

        Notes:
            - Extracted columns are created/updated in `self.df`.
            - On batch errors, rows in the batch are marked as "error".

        Example:
            pipeline.extract_information(cols=["salary", "technologies"], batch_size=8)
        """

        self.normalize_text(description_col_name)
        normalized_col = f"normalized_{description_col_name}"

        extractor = pipeline(
            task="text2text-generation",
            model=llm_name,
            max_new_tokens=max_tokens,
            device="cuda" if cuda.is_available() else "cpu",
        )

        field_prompts: Dict[str, str] = {
            "benefits": "List the employee benefits mentioned (health insurance, meal vouchers, etc). Answer only the benefits or 'not mentioned':",
            "salary": "What is the salary or compensation mentioned? Answer only the salary/range or 'not mentioned':",
            "requirements": "List the main requirements (skills, experience). Answer briefly or 'not mentioned':",
            "technologies": "List programming languages, tools and technologies mentioned. Answer only the list or 'not mentioned':",
            "contract_type": "What is the contract type (CLT, PJ, freelance)? Answer only the type or 'not mentioned':",
            "work_model": "Is it remote, hybrid or on-site? Answer only: remote/hybrid/on-site/not mentioned:",
            "experience_years": "How many years of experience required? Answer only the number/range or 'not mentioned':",
            "education": "What education level is required? Answer briefly or 'not mentioned':",
            "languages": "What languages are required (English, Spanish, etc)? Answer only the languages or 'not mentioned':",
            "company_size": "What is the company size? Answer only: startup/small/medium/large/not mentioned:",
        }

        for col in cols:
            self.df[col] = "not_specified"

        def truncate_text(text: str, max_chars: int = 800) -> str:
            """Trunca texto para evitar exceder limites do modelo."""
            if len(text) > max_chars:
                return text[:max_chars] + "..."
            return text

        total_rows = len(self.df)

        for field in cols:
            prompt_template = field_prompts.get(field, f"Extract {field} from this job description. Answer briefly or 'not mentioned':")

            print(f"\nExtracting: {field}")

            for start_idx in tqdm(range(0, total_rows, batch_size), desc=field):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_descriptions = self.df[normalized_col].iloc[start_idx:end_idx].tolist()

                prompts = [f"{prompt_template}\n\nJob: {truncate_text(desc)}\n\nAnswer:" for desc in batch_descriptions]

                try:
                    responses = extractor(prompts)

                    for i, response in enumerate(responses):
                        row_idx = start_idx + i
                        generated_text = response.get("generated_text", "") if isinstance(response, dict) else str(response)
                        cleaned = generated_text.strip().replace("\n", ", ")
                        if cleaned.lower() in ["not mentioned", "none", "n/a", ""]:
                            cleaned = "not_specified"
                        self.df.at[row_idx, field] = cleaned

                except Exception as e:
                    print(f"Erro no batch {start_idx}-{end_idx}: {e}")
                    for i in range(start_idx, min(end_idx, total_rows)):
                        self.df.at[i, field] = "error"

        print(f"\nExtraction completed. Created columns: {cols}")
    
    def extract_information_regex(self, cols: List[str], description_col_name: str = "raw_html_description") -> None:
        """Extract information using regex (fast and reliable for known patterns).

        Args:
            cols: List of fields to extract
            description_col_name: Name of the column with the job description
        """
        
        self.normalize_text(description_col_name)
        normalized_col = f'normalized_{description_col_name}'
        
        if normalized_col not in self.df:
            print(f"Coluna {normalized_col} não encontrada")
            return
        
        # regex patterns for each field
        extraction_patterns = {
            "work_model": {
                "remote": r"\b(remoto|remote|home\s*office|trabalho\s*remoto|100%\s*remoto|full\s*remote|fully\s*remote|wfh|work\s*from\s*home|trabajo\s*remoto|trabalhe\s*de\s*casa)\b",
                "hybrid": r"\b(h[ií]brido|hybrid|semi\s*presencial|presencial\s+e\s+remoto|remoto\s+e\s+presencial)\b",
                "on-site": r"\b(presencial|on\s*site|in\s*office|in\s*person|no\s*escrit[óo]rio)\b",
            },
            "contract_type": {
                "CLT": r"\b(clt|carteira\s*assinada|efetivo|regime\s*clt)\b",
                "PJ": r"\b(pj|pessoa\s*jur[íi]dica|cnpj|prestador|contractor)\b",
                "freelance": r"\b(freelance|freelancer|aut[ôo]nomo|freela)\b",
                "temporary": r"\b(tempor[áa]rio|temporary|contrato\s*tempor[áa]rio)\b",
                "internship": r"\b(est[áa]gio|internship|intern\b)\b",
            },
            "salary": {
                "pattern": r"(?:sal[áa]rio|remunera[çc][ãa]o|compensation|salary|pay|wage)[:\s]*(?:de\s+)?(?:r\$|brl|usd|\$)?\s*[\d\.,]+(?:\s*(?:a|to|-|–)\s*(?:r\$|brl|usd|\$)?\s*[\d\.,]+)?(?:\s*(?:k|mil|thousand|per\s+(?:month|year|m[êe]s|ano)))?",
            },
            "experience_years": {
                "pattern": r"(?:(\d+)\s*(?:\+|ou\s*mais|or\s*more|years?)?\s*(?:anos?|years?)\s*(?:de\s+)?(?:experi[êe]ncia|experience))|(?:(?:experi[êe]ncia|experience)\s*(?:de\s+)?(\d+)\s*(?:\+|ou\s*mais|or\s*more)?\s*(?:anos?|years?))|(?:(\d+)\s*(?:\+|a|\-|to)\s*(\d+)\s*(?:anos?|years?))",
            },
            "technologies": {
                "pattern": r"\b(python|java(?:script)?|typescript|react|angular|vue|node\.?js|sql|nosql|mongodb|postgresql|mysql|redis|docker|kubernetes|k8s|aws|azure|gcp|git|linux|spark|airflow|kafka|hadoop|terraform|jenkins|ci\s*/\s*cd|machine\s*learning|deep\s*learning|nlp|tensorflow|pytorch|scikit|pandas|numpy|power\s*bi|tableau|excel|r\b|scala|golang|go\b|rust|c\+\+|c#|\.net|php|ruby|rails|django|flask|fastapi|spring|kotlin|swift|flutter|react\s*native)\b",
            },
            "education": {
                "graduation": r"\b(gradua[çc][ãa]o|superior|bachelor|bacharelado|licenciatura|faculdade|universidade|degree)\b",
                "post_graduation": r"\b(p[óo]s[\-\s]?gradua[çc][ãa]o|especializa[çc][ãa]o|mba|post[\-\s]?graduate)\b",
                "masters": r"\b(mestrado|master['']?s?|m\.?sc\.?)\b",
                "phd": r"\b(doutorado|phd|ph\.?d\.?|doctor)\b",
            },
            "languages": {
                "english": r"\b(ingl[êe]s|english)\b",
                "spanish": r"\b(espanhol|spanish|castellano)\b",
                "portuguese": r"\b(portugu[êe]s|portuguese)\b",
                "french": r"\b(franc[êe]s|french)\b",
                "german": r"\b(alem[ãa]o|german|deutsch)\b",
            },
            "benefits": {
                "pattern": r"\b(vale[\-\s]?(?:refei[çc][ãa]o|alimenta[çc][ãa]o|transporte|vr|va|vt)|plano\s*de\s*sa[úu]de|assist[êe]ncia\s*m[ée]dica|dental|odontol[óo]gico|gympass|totalpass|seguro\s*de\s*vida|pln|plr|bonifica[çc][ãa]o|bonus|13[ºo]|f[ée]rias|day\s*off|birthday\s*off|stock\s*options|equity|a[çc][õo]es|aux[íi]lio[\-\s]?(?:creche|home\s*office|educa[çc][ãa]o)|health\s*insurance|401k)\b",
            },
        }
        
        for col in cols:
            self.df[col] = "not_specified"
        
        print(f"Extracting via regex: {cols}")
        
        for idx, row in tqdm(self.df.iterrows(), total=len(self.df), desc="Extracting"):
            text = row[normalized_col]
            
            for col in cols:
                if col not in extraction_patterns:
                    continue
                    
                patterns = extraction_patterns[col]
                
                if isinstance(patterns, dict) and "pattern" in patterns:
                    matches = re.findall(patterns["pattern"], text, re.IGNORECASE)
                    if matches:
                        flat_matches = []
                        for m in matches:
                            if isinstance(m, tuple):
                                flat_matches.extend([x for x in m if x])
                            else:
                                flat_matches.append(m)
                        unique_matches = list(dict.fromkeys(flat_matches))
                        self.df.at[idx, col] = ", ".join(unique_matches[:10])  # Limitar a 10
                else:
                    found = []
                    for category, pattern in patterns.items():
                        if re.search(pattern, text, re.IGNORECASE):
                            found.append(category)
                    if found:
                        self.df.at[idx, col] = ", ".join(found)
        
        print(f"Regex extraction completed. Created columns: {cols}")

    def run_pipeline(self, output_path: str, fallback_to_llm: bool = False) -> None:
        """Run the full pipeline (cleaning + regex extraction) and save CSV.

        Args:
            output_path: Path of the output CSV file.
            fallback_to_llm: If True, allow LLM fallback when detecting titles.
        """
        self.clean_job_raw_positions(fallback_to_llm=fallback_to_llm)
        self.clan_regions()
        self.extract_information_regex(
            cols=["work_model", "contract_type", "salary", "experience_years", "technologies", "education", "languages", "benefits"],
            description_col_name="raw_html_description",
        )
        self.save_cleaned_data(output_path)

    def _load_title_generator(self, model_name: str = "google/flan-t5-base") -> Any:
        """Lazily load and return a text generation pipeline.

        Args:
            model_name: Model identifier for `transformers.pipeline`.
        """
        if self._title_generator is None:
            # Lazy load to avoid paying the cost unless we really need the LLM fallback.
            self._title_generator = pipeline(
                task="text2text-generation",
                model=model_name,
                max_new_tokens=32,
                num_beams=4,
                device="cuda" if cuda.is_available() else "cpu",
            )
        return self._title_generator

    def _generate_title(self, text: str, description: str) -> str:
        """Generate a suggested title (via LLM) from `text` and `description`.

        The prompt asks the model to choose a single title among the keys
        defined in `ROLE_REGEX`. Returns an empty string on failure.

        Args:
            text: Title text extracted from the job posting.
            description: Job description (useful as additional context).

        Returns:
            Generated title string or empty string if an error occurred.
        """
        generator = self._load_title_generator()
        prompt = (
            "Task: Choose the best job title from the list below.\n"
            "list of job titles:\n"
            f"{list(ROLE_REGEX.keys())}" +
            "\n\n"
            "Rules:\n"
            "- Use ONLY one title from the list of job titles above.\n"
            "- The title choosed should be in the list of job titles above.\n"
            "- Output ONLY the title.\n\n"
            f"Job title: {text}\n"
            f"Job description: {description}\n\n"
            "Answer:"
        )
        try:
            result = generator(prompt)
        except Exception:
            return ""
        if not result:
            return ""
        return str(result[0].get("generated_text", "")).strip()