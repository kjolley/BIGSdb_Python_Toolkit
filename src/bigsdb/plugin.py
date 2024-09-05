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

import logging
import os
import json
import re
from collections import defaultdict
import bigsdb.utils
from bigsdb.base_application import BaseApplication
from bigsdb.job_manager import JobManager
from bigsdb.prefstore import Prefstore
from bigsdb.scheme_selector import SchemeSelector
from bigsdb.constants import DIRS, LOGS, LOCUS_PATTERN

MAX_ISOLATES_DROPDOWN = 1000


class Plugin(BaseApplication):
    def __init__(
        self,
        database=None,
        config_dir=DIRS["CONFIG_DIR"],
        dbase_config_dir=DIRS["DBASE_CONFIG_DIR"],
        arg_file=None,
        retrieving_attributes=False,
        logger=None,
        log_file=None,
        run_job=None,
    ):
        if not retrieving_attributes:
            if arg_file and database == None:
                raise ValueError("No database parameter passed.")
        self._init_logger(logger=logger, log_file=log_file, run_job=run_job)
        super(Plugin, self).__init__(
            database=database,
            config_dir=config_dir,
            dbase_config_dir=dbase_config_dir,
            logger=self.logger,
            testing=retrieving_attributes,
        )
        if arg_file != None:
            self._read_arg_file(arg_file)
        if retrieving_attributes:
            return
        self.cache = defaultdict(nested_defaultdict)
        att = self.get_attributes()
        if "offline_jobs" in att.get("requires", ""):
            self._initiate_job_manager()
        if run_job:
            self._initiate_job(run_job)
        else:
            self._initiate()

    # Override the following functions in subclass
    def get_attributes(self):
        raise NotImplementedError

    def get_hidden_attributes(self):
        return []

    def get_plugin_javascript(self):
        return ""

    def get_initiation_values(self):
        return {}

    def run(self):
        raise NotImplementedError

    def run_job(self, job_id):
        pass

    def _init_logger(self, logger=None, log_file=None, run_job=None):
        if logger:
            self.logger = logger
            return
        self.logger = logging.getLogger(__name__)
        if run_job:
            f_handler = logging.FileHandler(log_file or LOGS["JOBS_LOG"])
        else:
            f_handler = logging.FileHandler(log_file or LOGS["BIGSDB_LOG"])
        f_handler.setLevel(logging.INFO)
        f_format = logging.Formatter(
            "%(asctime)s - %(levelname)s: - %(module)s:%(lineno)d - %(message)s"
        )
        f_handler.setFormatter(f_format)
        self.logger.addHandler(f_handler)

    def _initiate(self):
        self.params = self.args.get("cgi_params")
        self.script_name = os.environ.get("SCRIPT_NAME", "") or "bigsdb.pl"
        self.username = self.args.get("username", "")
        self.email = self.args.get("email", "")
        self.datastore.initiate_view(
            username=self.args.get("username"),
            curate=self.args.get("curate", False),
            set_id=self.get_set_id(),
        )
        self.prefstore = Prefstore(
            data_connector=self.data_connector,
            config=self.config,
            logger=self.logger,
        )
        self._initiate_prefs()

    def _read_arg_file(self, arg_file):
        full_path = self.config.get("secure_tmp_dir") + f"/{arg_file}"
        if not os.path.isfile(full_path):
            self.logger.error(f"Argument file {full_path} does not exist.")
            self.args = {}
            return
        with open(full_path, "r") as f:
            self.args = json.load(f)

    def _initiate_job_manager(self):
        self.job_manager = JobManager(
            data_connector=self.data_connector,
            system=self.system,
            config=self.config,
            logger=self.logger,
        )

    def _initiate_job(self, job_id):
        self.params = self.job_manager.get_job_params(job_id)
        job = self.job_manager.get_job(job_id)

        self.datastore.initiate_view(
            username=job.get("username"),
            curate=self.params.get("curate"),
            set_id=self.params.get("set_id"),
        )

    def _initiate_prefs(self):
        self.set_pref_requirements()
        guid = self.args.get("guid")
        if self.system.get("dbtype", "") == "isolates":
            if self.pref_requirements.get("analysis") or self.pref_requirements.get(
                "query_field"
            ):
                locus_prefs = self.datastore.run_query(
                    "SELECT id,query_field,analysis FROM loci",
                    None,
                    {"fetch": "all_arrayref", "slice": {}},
                )
                self.prefs = defaultdict(nested_defaultdict)
                for locus in locus_prefs:
                    for action in ["query_field", "analysis"]:
                        self.prefs[action + "_loci"][locus["id"]] = locus[action]
                user_locus_prefs = self.prefstore.get_all_locus_prefs(
                    guid, self.system.get("db")
                )
                for prefs in user_locus_prefs:
                    if prefs["action"] in ["query_field", "analysis"]:
                        self.prefs[prefs["action"] + "_loci"][prefs["locus"]] = (
                            True if prefs["value"] == "true" else False
                        )
                scheme_prefs = self.datastore.run_query(
                    "SELECT id,query_field,analysis FROM schemes",
                    None,
                    {"fetch": "all_arrayref", "slice": {}},
                )
                for scheme in scheme_prefs:
                    for action in ["query_field", "analysis"]:
                        self.prefs[action + "_schemes"][scheme["id"]] = scheme[action]
                user_scheme_prefs = self.prefstore.get_all_scheme_prefs(
                    guid, self.system.get("db")
                )
                for prefs in user_scheme_prefs:
                    if prefs["action"] in ["query_field", "analysis"]:
                        self.prefs[prefs["action"] + "_schemes"][prefs["scheme_id"]] = (
                            True if prefs["value"] == "true" else False
                        )
                self.datastore.update_prefs(self.prefs)

    def is_curator(self):
        if self.username == None:
            return False
        user_info = self.datastore.get_user_info_from_username(self.username)
        if user_info == None or (user_info["status"] not in ["curator", "admin"]):
            return False
        return True

    def get_eav_group_icon(self, group):
        if group == None:
            return
        group_values = []
        if self.system.get("eav_groups"):
            group_values = self.system.get("eav_groups").split(",")
            for value in group_values:
                [name, icon] = value.split("|")
                if name == group:
                    return icon

    def print_bad_status(self, options):
        options["message"] = options.get("message", "Failed!")
        buffer = (
            '<div class="box statusbad" style="min-height:5em"><p>'
            + '<span class="failure fas fa-times fa-5x fa-pull-left"></span>'
            + '</p><p class="outcome_message">{0}</p>'.format(options.get("message"))
        )
        if options.get("detail"):
            buffer += '<p class="outcome_detail">{0}</p>'.format(options.get("detail"))
        buffer += "</div>"
        if not options.get("get_only"):
            print(buffer)
        return buffer

    def has_set_changed(self):
        set_id = self.args.get("set_id")
        if self.params.get("set_id") and set_id != None:
            if self.params.get("set_id") != set_id:
                self.print_bad_status(
                    {
                        "message": "The dataset has been changed since this plugin was "
                        "started. Please repeat the query."
                    }
                )
                return 1

    def get_set_id(self):
        if self.system.get("sets", "") == "yes":
            set_id = self.system.get("set_id") or self.params.get("set_id")
            if set_id != None and bigsdb.utils.is_integer(set_id):
                return set_id
            if self.datastore == None:
                return
            if self.system.get("only_sets", "") == "yes" and not self.args.get(
                "curate"
            ):
                if not self.cache.get("set_list"):
                    self.cache["set_list"] = self.datastore.run_query(
                        "SELECT id FROM sets ORDER BY display_order,description",
                        None,
                        {"fetch": "col_arrayref"},
                    )
                if len(self.cache.get("set_list", [])):
                    return self.cache.get("set_list")

    def _get_query(self, query_file):
        view = self.system.get("view")  # TODO Will need to initiate view
        if query_file == None:
            qry = f"SELECT * FROM {view} WHERE new_version IS NULL ORDER BY id"
        else:
            full_path = self.config.get("secure_tmp_dir") + "/" + query_file
            if os.path.exists(full_path):
                try:
                    with open(full_path) as x:
                        qry = x.read()
                except IOError:
                    if self.params.get("format", "") == "text":
                        print("Cannot open temporary file.")
                    else:
                        self.print_bad_status(
                            {"message": "Cannot open temporary file."}
                        )
                    self.logger.error(f"Cannot open temporary file {full_path}")
                    return
            else:
                if self.params.get("format", "") == "text":
                    print(
                        "The temporary file containing your query does "
                        "not exist. Please repeat your query."
                    )
                else:
                    self.print_bad_status(
                        {
                            "message": "The temporary file containing your query does "
                            "not exist. Please repeat your query."
                        }
                    )
        if self.system.get("dbtype", "") == "isolates":
            qry = re.sub(r"([\s\(])datestamp", r"\1view.datestamp", qry)
            qry = re.sub(r"([\s\(])date_entered", r"\1view.date_entered", qry)
        return qry

    def _get_ids_from_query(self, qry):
        if qry == None:
            return []
        qry = re.sub(r"ORDER\sBY.*$", "", qry)
        #       return if !$self->create_temp_tables($qry_ref); #TODO
        view = self.system.get("view")
        qry = re.sub(r"SELECT\s(view\.\*|\*)", "SELECT id", qry)
        qry += f" ORDER BY {view}.id"
        ids = self.datastore.run_query(qry, None, {"fetch": "col_arrayref"})
        return ids

    def get_selected_ids(self):
        query_file = self.params.get("query_file")
        if self.params.get("isolate_id"):
            selected_ids = self.params.get("isolate_id")
        elif query_file != None:
            qry = self._get_query(query_file)
            selected_ids = self._get_ids_from_query(qry)
        else:
            selected_ids = []
        return selected_ids

    def process_selected_ids(self):
        selected = self.params.get("isolate_id")
        ids = selected if selected else []
        pasted_cleaned_ids, invalid_ids = self._get_ids_from_pasted_list()
        ids.extend(pasted_cleaned_ids)
        if len(ids):
            id_set = set(ids)  # Convert to set to remove duplicates
            ids = list(dict.fromkeys(id_set))
        return ids, invalid_ids

    def print_seqbin_isolate_fieldset(self, options):
        seqbin_count = self.datastore.get_seqbin_count()
        print('<fieldset style="float:left"><legend>Isolates</legend>')
        if seqbin_count or options.get("use_all"):
            size = options.get("size", 8)
            list_box_size = size - 0.2
            print('<div style="float:left">')
            if (
                seqbin_count <= MAX_ISOLATES_DROPDOWN and not options["use_all"]
            ) or not options["isolate_paste_list"]:
                default = self.params.get("isolate_id")

                if default:
                    selected_ids = default
                else:
                    selected_ids = options.get("selected_ids", [])
                    # if len(selected_ids):
                    #    selected_ids = set(options.get('selected_ids', []))

                ids, labels = self.datastore.get_isolates_with_seqbin(options)
                print(
                    '<select name="isolate_id" id="isolate_id" '
                    f'style="min-width:12em;height:{size}em" multiple>'
                )
                for id in ids:
                    selected = " selected" if id in selected_ids else ""
                    label = labels.get(id, id)
                    print(f'<option value="{id}"{selected}>{label}</option>')
                print("</select>")
                list_button = ""
                if options["isolate_paste_list"]:
                    show_button_display = (
                        "none" if self.params.get("isolate_paste_list") else "display"
                    )
                    hide_button_display = (
                        "display" if self.params.get("isolate_paste_list") else "none"
                    )
                    list_button = (
                        '<input type="button" id="isolate_list_show_button" '
                        'onclick="isolate_list_show()" value="Paste list" '
                        f'style="margin:1em 0 0 0.2em; display:{show_button_display}" '
                        'class="small_submit" />'
                    )
                    list_button += (
                        '<input type="button" '
                        'id="isolate_list_hide_button" onclick="isolate_list_hide()" '
                        'value="Hide list" style="margin:1em 0 0 0.2em; '
                        f'display:{hide_button_display}" class="small_submit" />'
                    )
                print(
                    '<div style="text-align:center">'
                    '<input type="button" onclick="listbox_selectall(\'isolate_id\',true)" '
                    'value="All" style="margin-top:1em" class="small_submit" />'
                )
                print(
                    '<input type="button" onclick="listbox_selectall(\'isolate_id\',false)" '
                    'value="None" style="margin:1em 0 0 0.2em" class="small_submit" />'
                    f"{list_button}</div></div>"
                )
                if options["isolate_paste_list"]:
                    display = (
                        "block" if self.params.get("isolate_paste_list") else "none"
                    )
                    default = self.params.get("isolate_paste_list", "")
                    print(
                        '<div id="isolate_paste_list_div" style="float:left; '
                        f'display:{display}">'
                    )
                    print(
                        '<textarea name="isolate_paste_list" id="isolate_paste_list" '
                        f'style="height:{list_box_size}em" '
                        'placeholder="Paste list of isolate ids (one per line)...">'
                        f"{default}</textarea>"
                    )
            else:
                default = self.params.get("isolate_paste_list", "")
                print(
                    '<textarea name="isolate_paste_list" id="isolate_paste_list" '
                    f'style="height:{list_box_size}em" '
                    'placeholder="Paste list of isolate ids (one per line)...">'
                )
                if default:
                    print(default, end="")
                else:
                    print("\n".join(map(str, options.get("selected_ids"))), end="")
                print("</textarea>")
                print(
                    '<div style="text-align:center"><input type="button" '
                    "onclick=\"listbox_clear('isolate_paste_list')\" "
                    'value="Clear" style="margin-top:1em" class="small_submit" />'
                )
                if options.get("only_genomes"):
                    print(
                        '<input type="button" '
                        "onclick=\"listbox_listgenomes('isolate_paste_list')\" "
                        'value="List all" style="margin-top:1em" '
                        'class="small_submit" /></div>'
                    )
                else:
                    print(
                        '<input type="button" '
                        "onclick=\"listbox_listall('isolate_paste_list')\" "
                        'value="List all" style="margin-top:1em" '
                        'class="small_submit" /></div>'
                    )
            print("</div>")
        else:
            print("No isolates available<br />for analysis")
        print("</fieldset>")

    def print_action_fieldset(self, options=None):
        if options is None:
            options = {}
        page = options.get("page", self.params.get("page"))
        submit_name = options.get("submit_name", "submit")
        submit_label = options.get("submit_label", "Submit")
        reset_label = options.get("reset_label", "Reset")
        legend = options.get("legend", "Action")
        buffer = f'<fieldset style="float:left"><legend>{legend}</legend>\n'
        if "text" in options:
            buffer += options["text"]
        url = "{0}?db={1}&amp;page={2}".format(self.script_name, self.instance, page)
        fields = [
            "isolate_id",
            "id",
            "scheme_id",
            "table",
            "name",
            "ruleset",
            "locus",
            "profile_id",
            "simple",
            "set_id",
            "modify",
            "project_id",
            "edit",
            "private",
            "user_header",
            "interface",
        ]

        if "table" in options:
            raise NotImplementedError  # TODO datastore.get_table_pks
            pk_fields = self.datastore.get_table_pks(options["table"])
            fields.extend(pk_fields)
        for field in set(fields):
            if field in options:
                url += f"&amp;{field}={options[field]}"
        if not options.get("no_reset"):
            buffer += f'<a href="{url}" class="reset"><span>{reset_label}</span></a>\n'
        id = {"id": options["id"]} if "id" in options else {}
        buffer += (
            f'<input type="submit" id="{submit_name}" name="{submit_name}" '
            f'value="{submit_label}" class="submit" {id}>\n'
        )
        if "submit2" in options:
            options["submit2_label"] = options.get("submit2_label", options["submit2"])
            buffer += (
                f'<input type="submit" name="{options["submit2"]}" '
                f'value="{options["submit2_label"]}" class="submit" '
                'style="margin-left:0.2em">\n'
            )
        buffer += "</fieldset>"
        if not options.get("no_clear"):
            buffer += '<div style="clear:both"></div>'
        if options.get("get_only"):
            return buffer
        print(buffer)

    def start_form(self):
        print(
            f'<form method="post" action="{self.script_name}" enctype="multipart/form-data">'
        )

    def print_hidden(self, param_list):
        for param in param_list:
            if self.params.get(param):
                value = self.params.get(param)
                print(f'<input type="hidden" name="{param}" value="{value}" />')

    def end_form(self):
        print("</form>")

    def get_job_redirect(self, job_id):
        buffer = """
<div class="box" id="resultspanel">
<p>This job has been submitted to the queue.</p>
<p><a href="$self->{0}?db={1}&amp;page=job&amp;id={2}">
Follow the progress of this job and view the output.</a></p></div>
<script type="text/javascript">
setTimeout(function(){{
    window.location = "{0}?db={1}&page=job&id={2}";
}}, 2000);
</script>""".format(
            self.script_name, self.instance, job_id
        )
        return buffer

    def _get_ids_from_pasted_list(self):
        integer_ids = []
        cleaned_ids = []
        invalid_ids = []
        if self.params.get("isolate_paste_list"):
            list = self.params.get("isolate_paste_list").split("\n")
            for id in list:
                id = id.strip()
                if len(id) == 0:
                    continue
                if bigsdb.utils.is_integer(id):
                    integer_ids.append(int(id))
                else:
                    invalid_ids.append(id)
            for isolate_ids in bigsdb.utils.batch(integer_ids, 100):
                existing_ids = set(self.datastore.isolate_exists_batch(isolate_ids))
                for id in isolate_ids:
                    if id in existing_ids:
                        cleaned_ids.append(id)
                    else:
                        invalid_ids.append(id)
        return cleaned_ids, invalid_ids

    def print_isolate_fields_fieldset(self, options={}):
        set_id = self.get_set_id()
        is_curator = self.is_curator()
        fields = self.parser.get_field_list({"no_curate_only": not is_curator})
        optgroups = []
        labels = {}
        group_list = self.system.get("field_groups", "").split(",")
        group_members = {}
        attributes = self.parser.get_all_field_attributes()

        for field in fields:
            group = attributes[field].get("group", "General")
            group_members.setdefault(group, []).append(field)
            label = field.replace("_", " ")
            labels[field] = label
            if field == self.system.get("labelfield") and not options.get("no_aliases"):
                group_members["General"].append("aliases")
            if options.get("extended_attributes"):
                extended = self.get_extended_attributes()
                extatt = extended.get(field, [])
                if isinstance(extatt, list):
                    for extended_attribute in extatt:
                        extended_field = f"{field}___{extended_attribute}"
                        group_members.setdefault(group, []).append(extended_field)
                        labels[extended_field] = extended_attribute.replace("_", " ")

        for group in [None] + group_list:
            name = group or "General"
            name = name.split("|")[0]
            if name in group_members:
                optgroups.append({"name": name, "values": group_members[name]})
        html = []
        html.append('<fieldset style="float:left"><legend>Provenance fields</legend>')
        html.append(self.scrolling_list("fields", "fields", optgroups, labels, options))
        if not options.get("no_all_none"):
            html.append('<div style="text-align:center">')
            html.append(
                '<input type="button" onclick=\'listbox_selectall("fields",true)\' '
                'value="All" style="margin-top:1em" class="small_submit" />'
            )
            html.append(
                '<input type="button" onclick=\'listbox_selectall("fields",false)\' '
                'value="None" style="margin:1em 0 0 0.2em" class="small_submit" />'
            )
            html.append("</div>")
        html.append("</fieldset>")

        print("\n".join(html))

    def scrolling_list(self, name, id, items, labels, options):
        size = options.get("size", 8)
        default = options.get("default", [])
        if isinstance(items[0], dict):  # Check if items are optgroups
            options_html = "".join(
                [
                    self._generate_optgroup_html(optgroup, labels, default)
                    for optgroup in items
                ]
            )
        else:  # Handle simple list of values
            options_html = "".join(
                [
                    f'<option value="{value}"{" selected" if value in default else ""}>{labels.get(value, value)}</option>'
                    for value in items
                ]
            )
        return f'<select name="{name}" id="{id}" multiple="true" size="{size}">{options_html}</select>'

    def _generate_optgroup_html(self, optgroup, labels, default):
        name = optgroup["name"]
        values = optgroup["values"]
        options = "".join(
            [
                f'<option value="{value}"{" selected" if value in default else ""}>{labels.get(value, value)}</option>'
                for value in values
            ]
        )
        return f'<optgroup label="{name}">{options}</optgroup>'

    def get_extended_attributes(self):
        if not self.cache.get("extended_attributes"):
            data = self.datastore.run_query(
                "SELECT isolate_field,attribute FROM isolate_field_extended_attributes "
                "ORDER BY field_order",
                None,
                {"fetch": "all_arrayref", "slice": {}},
            )
            extended = {}
            for value in data:
                if not extended.get(value.get("isolate_field")):
                    extended[value["isolate_field"]] = []
                extended[value["isolate_field"]].append(value["attribute"])
            self.cache["extended_attributes"] = extended
        return self.cache.get("extended_attributes")

    def print_eav_fields_fieldset(self, options={}):
        eav_fields = self.datastore.get_eav_fields()
        if not eav_fields:
            return

        group_list = self.system.get("eav_groups", "").split(",")
        values = []
        labels = {}

        if group_list:
            eav_groups = {field["field"]: field["category"] for field in eav_fields}
            group_members = {}
            for eav_field in eav_fields:
                fieldname = eav_field["field"]
                labels[fieldname] = fieldname.replace("_", " ")
                if eav_groups.get(fieldname):
                    group_members.setdefault(eav_groups[fieldname], []).append(
                        fieldname
                    )
                else:
                    group_members.setdefault("General", []).append(fieldname)

            for group in [None] + group_list:
                name = group if group else "General"
                name = name.split("|")[0]
                if isinstance(group_members.get(name), list):
                    values.append({"name": name, "values": group_members[name]})
        else:
            values = self.datastore.get_eav_fieldnames()

        legend = self.system.get("eav_fields", "Secondary metadata")
        print(f'<fieldset style="float:left"><legend>{legend}</legend>')
        print(self.scrolling_list("eav_fields", "eav_fields", values, labels, options))

        if not options.get("no_all_none"):
            print(
                '<div style="text-align:center">'
                '<input type="button" onclick=\'listbox_selectall("eav_fields",true)\' '
                'value="All" style="margin-top:1em" class="small_submit" />'
                '<input type="button" onclick=\'listbox_selectall("eav_fields",false)\' '
                'value="None" style="margin:1em 0 0 0.2em" class="small_submit" />'
                "</div>"
            )
        print("</fieldset>")

    def print_isolates_locus_fieldset(self, options):
        print('<fieldset id="locus_fieldset" style="float:left"><legend>Loci</legend>')
        analysis_pref = options.get("analysis_pref", 1)
        locus_list, locus_labels = self.get_field_selection_list(
            {
                "loci": 1,
                "no_list_by_common_name": 1,
                "analysis_pref": analysis_pref,
                "query_pref": 0,
                "sort_labels": 1,
            }
        )

        if locus_list:
            print('<div style="float:left">')
            size = options.get("size", 8)
            list_box_size = size - 0.2

            try:
                print(
                    self.scrolling_list(
                        name="locus",
                        id="locus",
                        items=locus_list,
                        labels=locus_labels,
                        options={
                            "size": size,
                            "default": self.params.get("locus", []),
                        },
                    )
                )
            except Exception as e:
                print(f"Error generating list: {e}")

            print("</div>")

            if options.get("locus_paste_list"):
                display = "block" if self.params.get("locus_paste_list") else "none"
                print(
                    f'<div id="locus_paste_list_div" style="float:left; display:{display}">'
                )

                default = self.params.get("locus_paste_list", "")
                print(
                    '<textarea name="locus_paste_list" id="locus_paste_list" '
                    f'style="height:{list_box_size}em" '
                    'placeholder="Paste list of locus primary names (one per line)...">'
                )
                if default:
                    print(default, end="")

                print("</textarea>")

                print("</div>")

            print('<div style="clear:both"></div>')
            print('<div style="text-align:center">')
            if not options.get("no_all_none"):
                print(
                    '<input type="button" onclick=\'listbox_selectall("locus",true)\' '
                    'value="All" style="margin-top:1em" class="small_submit" />'
                )
                print(
                    '<input type="button" onclick=\'listbox_selectall("locus",false)\' '
                    'value="None" style="margin:1em 0 0 0.2em" class="small_submit" />'
                )

            if options.get("locus_paste_list"):
                show_button_display = (
                    "none" if self.params.get("locus_paste_list") else "display"
                )
                hide_button_display = (
                    "display" if self.params.get("locus_paste_list") else "none"
                )
                print(
                    '<input type="button" id="locus_list_show_button" '
                    "onclick='locus_list_show()' value=\"Paste list\" "
                    f'style="margin:1em 0 0 0.2em;display:{show_button_display}" '
                    'class="small_submit" />'
                )
                print(
                    '<input type="button" id="locus_list_hide_button" '
                    "onclick='locus_list_hide()' value=\"Hide list\" "
                    f'style="margin:1em 0 0 0.2em;display:{hide_button_display}" '
                    'class="small_submit" />'
                )

            print("</div>")
        else:
            print("No loci available<br />for analysis")
        print("</fieldset>")

    def get_field_selection_list(self, options={}):
        options.setdefault("query_pref", 1)
        options.setdefault("analysis_pref", 0)
        values = []

        if options.get("isolate_fields"):
            raise NotImplementedError

        if options.get("management_fields"):
            raise NotImplementedError

        if options.get("eav_fields"):
            raise NotImplementedError

        if options.get("loci"):
            loci = self._get_loci_list(options)
            values.extend(loci)

        if options.get("locus_extended_attributes"):
            raise NotImplementedError

        if options.get("scheme_fields"):
            raise NotImplementedError

        if options.get("lincodes"):
            raise NotImplementedError

        if options.get("classification_groups"):
            raise NotImplementedError

        if options.get("annotation_status"):
            raise NotImplementedError

        if options.get("sort_labels"):
            values = bigsdb.utils.dictionary_sort(values, self.cache["labels"])

        if options.get("optgroups"):
            raise NotImplementedError

        return values, self.cache["labels"]

    def _get_loci_list(self, options):
        if "locus_limit" in options:
            count = self.datastore.run_query("SELECT COUNT(*) FROM loci")
            if count > options["locus_limit"]:
                return []

        if not self.cache.get("loci"):
            locus_list = []
            common_names = self.datastore.run_query(
                "SELECT id, common_name FROM loci WHERE common_name IS NOT NULL",
                None,
                {"fetch": "all_hashref", "key": "id"},
            )
            set_id = self.get_set_id()
            loci = self.datastore.get_loci(
                {
                    "query_pref": options.get("query_pref", 1),
                    "analysis_pref": options.get("analysis_pref", 0),
                    "seq_defined": 0,
                    "do_not_order": 1,
                    "set_id": set_id,
                }
            )
            set_loci = (
                self.datastore.run_query(
                    "SELECT * FROM set_loci WHERE set_id=?",
                    set_id,
                    {"fetch": "all_hashref", "key": "locus"},
                )
                if set_id
                else {}
            )

            for locus in loci:
                locus_list.append(f"l_{locus}")
                self.cache["labels"][f"l_{locus}"] = locus
                set_name_is_set = False
                if set_id:
                    set_locus = set_loci.get(locus)
                    if set_locus and set_locus.get("set_name"):
                        self.cache["labels"][f"l_{locus}"] = set_locus["set_name"]
                        if set_locus.get("set_common_name"):
                            self.cache["labels"][
                                f"l_{locus}"
                            ] += f" ({set_locus['set_common_name']})"
                            if not options.get("no_list_by_common_name"):
                                locus_list.append(f"cn_{locus}")
                                self.cache["labels"][
                                    f"cn_{locus}"
                                ] = f"{set_locus['set_common_name']} ({set_locus['set_name']})"
                        set_name_is_set = True
                if (
                    not set_name_is_set
                    and common_names.get(locus)
                    and common_names[locus].get("common_name")
                ):
                    self.cache["labels"][
                        f"l_{locus}"
                    ] += f" ({common_names[locus]['common_name']})"
                    if not options.get("no_list_by_common_name"):
                        locus_list.append(f"cn_{locus}")
                        self.cache["labels"][
                            f"cn_{locus}"
                        ] = f"{common_names[locus]['common_name']} ({locus})"

            if self.prefs.get("locus_alias"):
                alias_sql = self.db.prepare("SELECT locus, alias FROM locus_aliases")
                try:
                    alias_sql.execute()
                except Exception as e:
                    logger.error(e)
                else:
                    for locus, alias in alias_sql.fetchall_arrayref():
                        if not self.cache["labels"].get(f"l_{locus}"):
                            continue
                        alias = alias.replace("_", " ")
                        locus_list.append(f"la_{locus}||{alias}")
                        self.cache["labels"][
                            f"la_{locus}||{alias}"
                        ] = f"{alias} [{self.cache['labels'][f'l_{locus}']}]"

            locus_list.sort(key=lambda x: self.cache["labels"][x].lower())
            locus_list = list(
                dict.fromkeys(locus_list)
            )  # Remove duplicates while preserving order
            self.cache["loci"] = locus_list

        return self.cache["loci"]

    def set_pref_requirements(self):
        self.pref_requirements = {"analysis": 1, "query_field": 1}

    def get_selected_loci(self, options={}):
        self._escape_params()
        loci = self.params.get("locus", "")

        loci_selected = []
        if self.system["dbtype"] == "isolates":
            pattern = re.compile(LOCUS_PATTERN)
            for locus in loci:
                match = pattern.match(locus)
                locus_name = match.group(1) if match else None
                if locus_name:
                    loci_selected.append(locus_name)
        else:
            loci_selected = loci
        pasted_cleaned_loci, invalid_loci = self._get_loci_from_pasted_list()

        loci_selected.extend(pasted_cleaned_loci)
        if options.get("scheme_loci"):
            scheme_loci = self._get_selected_scheme_loci(options)
            loci_selected.extend(scheme_loci)
        loci_selected = list(set(loci_selected))  # Remove duplicates
        invalid_loci = list(set(invalid_loci))
        return loci_selected, invalid_loci

    def _get_loci_from_pasted_list(self):
        cleaned_loci = []
        invalid_loci = []
        if self.params.get("locus_paste_list"):
            loci_list = self.params["locus_paste_list"].split("\n")
            for locus in loci_list:
                if not locus.strip():
                    continue
                locus = locus.strip()
                set_id = self.get_set_id()
                if set_id:
                    real_name = self.datastore.get_set_locus_real_id(locus, set_id)
                else:
                    real_name = locus
                if self.datastore.is_locus(real_name):
                    cleaned_loci.append(real_name)
                else:
                    invalid_loci.append(locus)
        return cleaned_loci, invalid_loci

    def _get_selected_scheme_loci(self, options={}):
        scheme_ids = self.datastore.run_query(
            "SELECT id FROM schemes", None, {"fetch": "col_arrayref"}
        )
        scheme_ids.append(0)

        selected_schemes = []
        loci = []

        for scheme_id in scheme_ids:
            if not self.params.get(f"s_{scheme_id}"):
                continue
            selected_schemes.append(scheme_id)
            if options.get("delete_params"):
                self.params.pop(f"s_{scheme_id}")
        set_id = self.get_set_id()

        for scheme_id in selected_schemes:
            if scheme_id:
                scheme_loci = self.datastore.get_scheme_loci(scheme_id)
            else:
                scheme_loci = self.datastore.get_loci_in_no_scheme({"set_id": set_id})

            loci.extend(scheme_loci)

        return loci

    def _escape_params(self):
        escapes = {
            "__prime__": "'",
            "__slash__": "\\",
            "__comma__": ",",
            "__space__": " ",
            "_OPEN_": "[",
            "_CLOSE_": "]",
            "_GT_": ">",
        }
        param_names = list(self.params.keys())
        for param_name in param_names:
            key = param_name
            if any(escape_string in param_name for escape_string in escapes.keys()):
                for escape_string, replacement in escapes.items():
                    key = key.replace(escape_string, replacement)
                self.params[key] = self.params.pop(param_name)

    def print_scheme_fieldset(self, options={}):
        analysis_pref = options.get("analysis_pref", 1)
        print(
            '<fieldset id="scheme_fieldset" style="float:left"><legend>Schemes</legend>'
            '<noscript><p class="highlight">Enable Javascript to select schemes.</p></noscript>'
            '<div id="tree" class="tree" style="height:14em;width:20em">'
        )

        set_id = self.get_set_id()
        scheme_selector = SchemeSelector(
            datastore=self.datastore,
            prefs=self.prefs,
            params=self.params,
            set_id=set_id,
        )
        print(
            scheme_selector.get_tree(
                {"select_schemes": 1, "analysis_pref": analysis_pref}
            )
        )

        print("</div>")

        if options.get("fields_or_loci"):
            print('<div style="padding-top:1em"><ul><li>')
            print(
                '<input type="checkbox" name="scheme_fields" checked> '
                "Include all fields from selected schemes"
            )

            print("</li><li>")
            print(
                '<input type="checkbox" name="scheme_members" checked> '
                "Include all loci from selected schemes"
            )

            print("</li></ul></div>")

        print("</fieldset>")


# Function to create a nested defaultdict
def nested_defaultdict():
    return defaultdict(nested_defaultdict)
