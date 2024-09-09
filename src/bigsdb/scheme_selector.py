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


class SchemeSelector:
    def __init__(self, datastore, prefs, params, set_id=None):
        self.datastore = datastore
        self.prefs = prefs
        self.params = params
        self.set_id = set_id

    def get_tree(self, options={}):

        groups_with_no_parent = self.datastore.run_query(
            "SELECT id FROM scheme_groups WHERE id NOT IN (SELECT group_id FROM "
            "scheme_group_group_members) ORDER BY display_order,name",
            None,
            {"fetch": "col_arrayref"},
        )

        buffer = ""

        for group in groups_with_no_parent:
            group_info = self.datastore.get_scheme_group_info(group)
            group_scheme_buffer = self._get_group_schemes(group, options)
            child_group_buffer = self._get_child_groups(group, 1, options)
            if not group_scheme_buffer and not child_group_buffer:
                continue

            buffer += f"<li><a>{group_info['name']}</a>\n"
            buffer += group_scheme_buffer
            buffer += child_group_buffer
            buffer += "</li>\n"

        buffer += self._add_schemes_not_in_groups(
            {
                "options": options,
                "groups_with_no_parent": groups_with_no_parent,
                "page": self.params["page"],
            }
        )

        loci_not_in_schemes = self.datastore.get_loci_in_no_scheme(
            {"set_id": self.set_id}
        )
        if not options.get("schemes_only") and loci_not_in_schemes:
            id_attr = ' id="s_0"' if options.get("select_schemes") else ""
            buffer += f"<li{id_attr}><a>Loci not in schemes</a>\n"
            buffer += "</li>\n"

        if buffer:
            if options.get("schemes_only"):
                return f"<ul>{buffer}</ul>"
            main_buffer = "<ul>\n"
            main_buffer += '<li id="all_loci" data-jstree=\'{"opened":true}\'><a>All loci</a><ul>\n'
            main_buffer += buffer
            main_buffer += "</ul>\n</li></ul>\n"
        else:
            main_buffer = "<ul><li><a>No loci available for analysis.</a></li></ul>\n"

        if options.get("get_groups"):
            groups = set()
            for match in re.findall(r"group_id=(\d+)", main_buffer):
                groups.add(match)
            return groups

        return main_buffer

    def _get_group_schemes(self, group_id, options={}):

        buffer = ""
        set_clause = (
            f" AND scheme_id IN (SELECT scheme_id FROM set_schemes WHERE set_id={set_id})"
            if self.set_id
            else ""
        )

        schemes = self.datastore.run_query(
            "SELECT scheme_id FROM scheme_group_scheme_members m LEFT JOIN schemes s ON "
            f"s.id=m.scheme_id WHERE m.group_id=? {set_clause} ORDER BY display_order,name",
            group_id,
            {"fetch": "col_arrayref"},
        )

        if schemes:
            for scheme_id in schemes:
                if options.get("isolate_display") and not self.prefs[
                    "isolate_display_schemes"
                ].get(scheme_id):
                    continue
                if options.get("analysis_pref") and not self.prefs[
                    "analysis_schemes"
                ].get(scheme_id):
                    continue
                if options.get("no_disabled") and self.prefs["disable_schemes"].get(
                    scheme_id
                ):
                    continue

                scheme_info = self.datastore.get_scheme_info(
                    scheme_id, {"set_id": self.set_id}
                )

                scheme_info["name"] = scheme_info["name"].replace("&", "&amp;")

                id_attr = (
                    f' id="s_{scheme_id}"' if options.get("select_schemes") else ""
                )
                buffer += f'<li{id_attr}><a>{scheme_info["name"]}</a></li>\n'

        return f"<ul>{buffer}</ul>\n" if buffer else ""

    def _get_child_groups(self, group_id, level, options={}):

        buffer = ""
        child_groups = self.datastore.run_query(
            "SELECT id FROM scheme_groups LEFT JOIN scheme_group_group_members ON "
            "scheme_groups.id=group_id WHERE parent_group_id=? ORDER BY display_order,name",
            group_id,
            {"fetch": "col_arrayref"},
        )

        if child_groups:
            for group_id in child_groups:
                group_info = self.datastore.get_scheme_group_info(group_id)
                new_level = level
                if new_level == 10:
                    break  # prevent runaway if child is set as the parent of a parental group

                group_scheme_buffer = self._get_group_schemes(group_id, options)
                child_group_buffer = self._get_child_groups(
                    group_id, new_level + 1, options
                )

                if group_scheme_buffer or child_group_buffer:
                    page = self.params.get("page")
                    if options.get("schemes_only"):
                        buffer += f'<li>{group_info["name"]}\n'
                    else:
                        buffer += f'<li><a>{group_info["name"]}</a>\n'
                    buffer += group_scheme_buffer
                    buffer += child_group_buffer
                    buffer += "</li>"

        return f"<ul>\n{buffer}</ul>\n" if buffer else ""

    def _add_schemes_not_in_groups(self, args):
        options = args.get("options", {})
        groups_with_no_parent = args.get("groups_with_no_parent", [])
        page = args.get("page", "")
        schemes_not_in_group = self._get_schemes_not_in_groups(options)
        buffer = ""

        if schemes_not_in_group:
            data_exists = False
            temp_buffer = ""

            if groups_with_no_parent:
                if options.get("schemes_only"):
                    temp_buffer += "<li>Other schemes<ul>"
                else:
                    temp_buffer += "<li><a>Other schemes</a><ul>"

            for scheme in schemes_not_in_group:
                if not self._should_display_scheme_in_tree(scheme["id"], options):
                    continue

                scheme["name"] = scheme["name"].replace("&", "&amp;")

            if groups_with_no_parent:
                temp_buffer += "</ul></li>"

            if data_exists:
                buffer += temp_buffer

        return buffer

    def _get_schemes_not_in_groups(self, options={}):
        set_id = self.set_id
        set_clause = (
            f"AND id IN (SELECT scheme_id FROM set_schemes WHERE set_id={set_id})"
            if set_id
            else ""
        )

        no_submission_clause = (
            " AND id IN (SELECT scheme_id FROM scheme_members sm JOIN loci l ON "
            "sm.locus=l.id WHERE NOT l.no_submissions OR l.no_submissions IS NULL)"
            if options.get("filter_no_submissions")
            else ""
        )

        schemes = self.datastore.run_query(
            "SELECT id FROM schemes WHERE id NOT IN (SELECT scheme_id FROM "
            f"scheme_group_scheme_members) {set_clause}{no_submission_clause} ORDER "
            "BY display_order,name",
            None,
            {"fetch": "col_arrayref", "slice": {}},
        )

        not_in_group = []
        for scheme_id in schemes:
            if self.prefs["disable_schemes"].get(scheme_id) and options.get(
                "no_disabled"
            ):
                continue
            scheme_info = self.datastore.get_scheme_info(scheme_id, {"set_id": set_id})
            not_in_group.append({"id": scheme_id, "name": scheme_info["name"]})

        return not_in_group

    def _should_display_scheme_in_tree(self, scheme_id, options):
        if options.get("isolate_display") and not self.prefs[
            "isolate_display_schemes"
        ].get(scheme_id):
            return False
        if options.get("analysis_pref") and not self.prefs["analysis_schemes"].get(
            scheme_id
        ):
            return False
        return True
