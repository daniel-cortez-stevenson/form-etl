import argparse
import logging

from apache_beam.options.pipeline_options import PipelineOptions

from form_etl.pipeline import form_events as beam_pipeline


def main(known_args, beam_options):
    beam_pipeline.run(
        **vars(known_args),
        beam_options=beam_options,
    )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap_servers", default="localhost:9092")
    parser.add_argument("--topics", default="form.events")
    parser.add_argument("--group_id", default="form_etl")
    parser.add_argument("--form_event_output_path", default="./form_event/")
    parser.add_argument("--form_field_output_path", default="./form_field/")
    parser.add_argument("--max_num_records", type=int, default=None)

    known_args, beam_args = parser.parse_known_args()

    beam_options = PipelineOptions(beam_args)

    main(known_args, beam_options)
