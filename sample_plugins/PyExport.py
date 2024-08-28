# Written by Keith Jolley
# Copyright (c) 2024, University of Oxford
# E-mail: keith.jolley@biology.ox.ac.uk
#
# This file is part of BIGSdb Python Toolkit.
#
# BIGSdb Python Toolkit is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BIGSdb Python Toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not,
# see <https://www.gnu.org/licenses/>.

import os
from pathlib import Path
import bigsdb.utils
from bigsdb.plugin import Plugin


class PyExport(Plugin):
    def get_attributes(self):
        return {
            "name": "Export (PYTHON TEST)",
            "authors": [
                {
                    "name": "Keith Jolley",
                    "affiliation": "University of Oxford, UK",
                    "email": "keith.jolley@biology.ox.ac.uk",
                }
            ],
            "description": "Export dataset generated from query results",
            "full_description": "The Export plugin creates a download file "
            "of any primary metadata, secondary metadata, allele designations, "
            "scheme designations, or publications for isolates within a "
            "selected dataset or for the whole database. The output file is "
            "in Excel format.",
            "category": "Export",
            "menutext": "Dataset (Python test)",
            "module": "PyExport",
            "version": "1.0.0",
            "section": "export,postquery",
            "url": "{0}/data_export/isolate_export.html".format(
                self.config.get("doclink")
            ),
            "input": "query",
            "requires": "ref_db,js_tree,offline_jobs",
            "help": "tooltips",
            "order": 15,
            "dbtype": "isolates",
            "image": None,
            "system_flag": "DatasetExport",
            "enabled_by_default": 1,
        }

    def run(self):
        print("<h1>Export dataset</h1>")
        if self.system.get("DatasetExport", "") == "no":
            self.print_bad_status({"message": "Dataset exports are disabled."})
            return
        if self.has_set_changed():
            return
        if self.params.get("submit"):
            self._submit()
            return
        self._print_interface()

    def _print_interface(self):
        set_id = self.get_set_id()
        selected_ids = self.get_selected_ids()
        print(
            '<div class="box" id="queryform"><div class="scrollable">'
            "<p>Currently this is just a demonstration of a plugin that uses the "
            "offline job manager. You can select isolate ids and fields and the job "
            "will get sent to the queue. When run, it will create a tab-delimited "
            "text file and an Excel file containing the primary metadata for "
            "each selected isolate record.</p>"
            "<p>New methods will be added later to support selecting specific fields, "
            "loci, and schemes.</p>"
        )
        self.start_form()
        self.print_seqbin_isolate_fieldset(
            {
                "use_all": 1,
                "selected_ids": selected_ids,
                "isolate_paste_list": 1,
            }
        )
        self.print_isolate_fields_fieldset(
            {
                "extended_attributes": 1,
                "default": ["id", self.system.get("labelfield")],
                "no_all_none": 1,
            }
        )
        self.print_eav_fields_fieldset({"no_all_none": 1})
        self.print_isolates_locus_fieldset({"locus_paste_list": 1, "no_all_none": 1})
        self.print_action_fieldset({"no_reset": 1})
        self.print_hidden(["db", "page", "name", "set_id"])
        self.end_form()
        print("</div></div>")

    def _submit(self):
        ids, invalid_ids = self.process_selected_ids()
        if len(ids) == 0:
            self.print_bad_status({"message": "No valid ids have been selected!"})
            self._print_interface()
            return
        if len(invalid_ids):
            list_string = ", ".join(map(str, invalid_ids))
            self.print_bad_status(
                {
                    "message": f"The following isolates in your pasted list are invalid: {list_string}."
                }
            )
            self._print_interface()
            return
        if not self.params.get("fields") and not self.params.get("eav_fields"):
            self.print_bad_status(
                {"message": f"You need to select at least one field."}
            )
            self._print_interface()
            return
        loci, invalid_loci = self.get_selected_loci()
        if len(invalid_loci):
            list_string = ", ".join(map(str, invalid_loci))
            self.print_bad_status(
                {
                    "message": f"The following loci in your pasted list are invalid: {list_string}."
                }
            )
            self._print_interface()
            return
        attributes = self.get_attributes()
        if self.args.get("curate"):
            self.params["curate"] = 1
        if self.args.get("set_id"):
            self.params["set_id"] = self.args.get("set_id")
        job_id = self.job_manager.add_job(
            {
                "dbase_config": self.instance,
                "ip_address": self.params.get("remote_host"),
                "module": attributes.get("module"),
                "priority": attributes.get("priority"),
                "parameters": self.params,
                "isolates": ids,
                "loci": loci,
                "username": self.username,
                "email": self.email,
            }
        )
        print(self.get_job_redirect(job_id))

    def get_initiation_values(self):
        return {"jQuery.jstree": 1, "jQuery.multiselect": 1}

    def _get_selected_eav_fields(self):
        eav_fields = []
        param_eav_fields = self.params.get("eav_fields", "").split("||")
        for field in param_eav_fields:
            if self.datastore.is_eav_field(field):
                eav_fields.append(field)
        return eav_fields

    def _get_header(self, job_id):
        param_fields = self.params.get("fields", "").split("||")
        header = []
        for field in param_fields:
            if self.parser.is_field(field):
                header.append(field)
            elif "___" in field:  # Extended attribute
                header.append(field.split("___")[1])
        eav_fields = self._get_selected_eav_fields()
        header.extend(eav_fields)
        loci = self.job_manager.get_job_loci(job_id)
        header.extend(loci)
        return header

    def _get_prov_fields(self):
        param_fields = self.params.get("fields", "").split("||")
        fields = []
        for field in param_fields:
            if self.parser.is_field(field):
                fields.append(field)
        return fields

    def run_job(self, job_id):
        view = self.system.get("view")
        ids = self.job_manager.get_job_isolates(job_id)
        isolate_table = self.datastore.create_temp_list_table_from_list("int", ids)
        loci = self.job_manager.get_job_loci(job_id)
        locus_table = self.datastore.create_temp_list_table_from_list("text", loci)
        outfile = f"{self.config['tmp_dir']}/{job_id}.txt"
        param_fields = self.params.get("fields", "").split("||")
        header = self._get_header(job_id)
        fields = self._get_prov_fields()
        if "id" not in fields:
            fields.insert(0, "id")

        qry = (
            f"SELECT "
            + ",".join(fields)
            + f" FROM {view} v JOIN {isolate_table} l ON v.id=l.value ORDER BY id"
        )
        results = self.datastore.run_query(
            qry, None, {"fetch": "all_arrayref", "slice": {}}
        )
        eav_fields = self._get_selected_eav_fields()
        last_progress = 0
        total = len(results)
        with open(outfile, "w") as f:
            f.write("\t".join(header) + "\n")
            i = 0
            for record in results:
                row_values = []
                for field in param_fields:
                    if self.parser.is_field(field):
                        row_values.append(record.get(field, ""))
                    elif "___" in field:  # Extended attribute
                        ext_value = self._get_extended_attribute_value(record, field)
                        row_values.append(ext_value or "")
                for field in eav_fields:
                    row_values.append(
                        str(
                            self.datastore.get_eav_field_value(record["id"], field)
                            or ""
                        )
                    )
                i += 1
                f.write(
                    "\t".join(self._convert_to_string(value) for value in row_values)
                    + "\n"
                )
                progress = int(80 * (i / total))
                if progress > last_progress:
                    last_progress = progress
                    self.job_manager.update_job_status(
                        job_id, {"percent_complete": progress}
                    )
        if not Path(outfile).is_file():
            self.logger.error(f"File {outfile} does not exist")
            return
        self.job_manager.update_job_output(
            job_id,
            {
                "filename": f"{job_id}.txt",
                "description": "01_Export table (text)",
                "compress": 1,
                "keep_original": 1,  # Original needed to generate Excel file
            },
        )
        self.job_manager.update_job_status(
            job_id, {"percent_complete": 80, "stage": "Creating Excel file"}
        )
        excel_file = bigsdb.utils.text2excel(
            outfile,
            {
                "worksheet": "Export",
                "text_fields": self.system.get("labelfield"),
            },
        )
        if Path(excel_file).is_file():
            self.job_manager.update_job_output(
                job_id,
                {
                    "filename": f"{job_id}.xlsx",
                    "description": "01_Export table (Excel)",
                    "compress": 1,
                },
            )

        if Path(f"{outfile}.gz").is_file():
            Path(outfile).unlink()

    def _convert_to_string(self, value):
        if value is None:
            return ""
        elif isinstance(value, list):
            return ";".join(map(str, value))
        else:
            return str(value)

    def _get_extended_attribute_value(self, record, field):
        isolate_field, attribute = field.split("___")
        if record.get(isolate_field, "") == "":
            return ""
        if not self.cache["extended_attributes"][attribute][record[isolate_field], ""]:
            self.cache["extended_attributes"][attribute][
                record.get(isolate_field)
            ] = self.datastore.run_query(
                "SELECT value FROM isolate_value_extended_attributes WHERE "
                "(isolate_field,attribute,field_value)=(?,?,?)",
                [
                    isolate_field,
                    attribute,
                    record[isolate_field],
                ],
            )
        return self.cache["extended_attributes"][attribute][record[isolate_field]] or ""

    def get_plugin_javascript(self):
        return """
$(document).ready(function(){ 
    $('#fields,#eav_fields,#composite_fields,#locus,#classification_schemes').multiselect({
         classes: 'filter',
         menuHeight: 250,
         menuWidth: 400,
         selectedList: 8
      });
    $('#locus').multiselectfilter();
});
"""
