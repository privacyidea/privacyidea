import {
  Component,
  computed,
  effect,
  EventEmitter,
  input,
  linkedSignal,
  OnInit,
  Output,
  signal,
  WritableSignal
} from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";

import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatTableModule } from "@angular/material/table";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatDivider } from "@angular/material/list";
import { MatError } from "@angular/material/form-field";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";

export type AttributeMappingRow = {
  privacyideaAttr: string | null;
  userStoreAttr: string;
};

@Component({
  selector: "app-http-resolver",
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatError,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider,
    MatButtonToggleGroup,
    MatButtonToggle
  ],
  templateUrl: "./http-resolver.component.html",
  styleUrl: "./http-resolver.component.scss"
})
export class HttpResolverComponent implements OnInit {
  protected readonly privacyideaAttributes: string[] = [
    "userid",
    "givenname",
    "username",
    "email",
    "surname",
    "phone",
    "mobile"
  ];
  protected readonly displayedColumns: string[] = ["privacyideaAttr", "userStoreAttr", "actions"];
  protected readonly CUSTOM_ATTR_VALUE = "__custom__";
  data = input<any>({});
  type = input<string>("httpresolver");
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();
  isAdvanced: boolean = false;
  isAuthorizationExpanded: boolean = false;
  endpointControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  methodControl = new FormControl<string>("GET", { nonNullable: true, validators: [Validators.required] });
  requestMappingControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  headersControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  responseMappingControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  errorResponseControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  baseUrlControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  tenantControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  clientIdControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  clientSecretControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  protected basicSettings: WritableSignal<boolean> = signal(true);
  protected defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "userid" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenname" }
  ]);
  protected mappingRows = linkedSignal<AttributeMappingRow[]>(() => {
    const existing = this.data()?.attribute_mapping;
    if (existing && Object.keys(existing).length > 0) {
      return Object.entries(existing).map(([privacyideaAttr, userStoreAttr]) => ({
        privacyideaAttr,
        userStoreAttr: userStoreAttr as string
      }));
    }
    return this.defaultMapping();
  });
  protected availableAttributes = computed(() => {
    const rows = this.mappingRows();
    return rows.map((_, rowIndex) => {
      const selectedAttributes = rows
        .filter((_, i) => i !== rowIndex)
        .map(row => row.privacyideaAttr);
      return this.privacyideaAttributes.filter(attr => !selectedAttributes.includes(attr));
    });
  });

  constructor() {
    effect(() => {
      this.initializeData();
      this.syncControls();
      this.emitControls();
    });
  }

  ngOnInit(): void {
    if (this.isAdvanced) {
      this.basicSettings.set(false);
    }
  }

  protected syncControls(): void {
    const data = this.data();
    if (!data) return;

    if (data.endpoint !== undefined) this.endpointControl.setValue(data.endpoint, { emitEvent: false });
    if (data.method !== undefined) this.methodControl.setValue(data.method, { emitEvent: false });
    if (data.requestMapping !== undefined) this.requestMappingControl.setValue(data.requestMapping, { emitEvent: false });
    if (data.headers !== undefined) this.headersControl.setValue(data.headers, { emitEvent: false });
    if (data.responseMapping !== undefined) this.responseMappingControl.setValue(data.responseMapping, { emitEvent: false });
    if (data.errorResponse !== undefined) this.errorResponseControl.setValue(data.errorResponse, { emitEvent: false });
    if (data.base_url !== undefined) this.baseUrlControl.setValue(data.base_url, { emitEvent: false });
    if (data.tenant !== undefined) this.tenantControl.setValue(data.tenant, { emitEvent: false });
    if (data.client_id !== undefined) this.clientIdControl.setValue(data.client_id, { emitEvent: false });
    if (data.client_secret !== undefined) this.clientSecretControl.setValue(data.client_secret, { emitEvent: false });
  }

  protected emitControls(): void {
    const controls: { [key: string]: FormControl<any> } = {};
    const data = this.data();

    if (!this.isAdvanced && this.basicSettings()) {
      controls["endpoint"] = this.endpointControl;
      controls["method"] = this.methodControl;
      controls["requestMapping"] = this.requestMappingControl;
      controls["headers"] = this.headersControl;
      controls["responseMapping"] = this.responseMappingControl;

      if (data?.hasSpecialErrorHandler) {
        controls["errorResponse"] = this.errorResponseControl;
      }
    } else {
      controls["base_url"] = this.baseUrlControl;

      if (this.type() === "entraidresolver") {
        controls["tenant"] = this.tenantControl;
        controls["client_id"] = this.clientIdControl;

        if (data?.client_credential_type === "secret" || !data?.client_credential_type) {
          controls["client_secret"] = this.clientSecretControl;
        }
      }
    }

    this.additionalFormFieldsChange.emit(controls);
  }

  protected initializeData(): void {
    const data = this.data();
    if (!data) return;

    const configs = [
      "config_authorization",
      "config_user_auth",
      "config_get_user_list",
      "config_get_user_by_id",
      "config_get_user_by_name",
      "config_create_user",
      "config_edit_user",
      "config_delete_user"
    ];
    configs.forEach(c => {
      if (!data[c]) {
        data[c] = {};
      }
    });

    const existing = data?.attribute_mapping as Record<string, string> | undefined;

    if (!existing || Object.keys(existing).length === 0) {
      this.syncMappingToData();
    }
  }

  isCustomAttr(value: string | null): boolean {
    return value === this.CUSTOM_ATTR_VALUE;
  }

  setCustomAttr(rowIndex: number, customValue: string): void {
    const v = (customValue ?? "").trim();
    const rows = [...this.mappingRows()];
    rows[rowIndex].privacyideaAttr = v ? v : null;
    this.mappingRows.set(rows);
    this.onMappingChanged();
  }

  onPrivacyIdeaAttrChanged(rowIndex: number): void {
    if (this.mappingRows()[rowIndex].privacyideaAttr === this.CUSTOM_ATTR_VALUE) return;
    this.onMappingChanged();
  }

  addMappingRow(): void {
    this.mappingRows.update(rows => [
      ...rows,
      { privacyideaAttr: null, userStoreAttr: "" }
    ]);
    this.syncMappingToData();
  }

  removeMappingRow(index: number): void {
    this.mappingRows.update(rows => rows.filter((_, i) => i !== index));
    this.syncMappingToData();
  }

  protected onMappingChanged(): void {
    this.mappingRows.set([...this.mappingRows()]);
    this.syncMappingToData();
  }

  private syncMappingToData(): void {
    const map: Record<string, string> = {};

    for (const row of this.mappingRows()) {
      const k = (row.privacyideaAttr ?? "").trim();
      const v = (row.userStoreAttr ?? "").trim();
      if (k && v) {
        map[k] = v;
      }
    }

    (this.data() as any).attribute_mapping = map;
  }
}
