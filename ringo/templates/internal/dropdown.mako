<%
  value = field.get_value()
  if not isinstance(value, list):
    value = [value]
%>
% if field.readonly:
  <div class="readonlyfield" name="${field.name}" value="${field.get_value()}">
    % if field.get_previous_value() is not None:
      ${renderer._render_diff(_(field.get_previous_value("", expand=True)),
        field.renderer.render_link() or _(field.get_value(expand=True)) or  h.literal("&nbsp;"))}
    % else:
      ${field.renderer.render_link() or _(field.get_value(expand=True)) or h.literal("&nbsp;")}
    % endif
    % for v in value:
      <input type="hidden" name="${field.name}" value="${v}"/>
    % endfor
  </div>
% else:
  <select class="form-control" id="${field.id}" name="${field.name}" datatype="${get_field_type(field)}">
    % for option in options:
      ## Depending if the options has passed the configured filter the
      ## option will be visible or hidden
      % if option[2]:
        % if option[1] in value:
          <option value="${option[1]}" selected="selected">${_(option[0])} </option>
        % else:
          <option value="${option[1]}">${_(option[0])}</option>
        % endif
      % elif option[1] in value and not field.renderer.remove_filtered == "true":
        <option value="${option[1]}" selected="selected">${_(option[0])}</option>
      % endif
    % endfor
  </select>
% endif
