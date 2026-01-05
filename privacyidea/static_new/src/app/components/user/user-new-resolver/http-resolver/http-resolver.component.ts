import {
  Component,
  computed,
  EventEmitter,
  input,
  linkedSignal,
  OnInit,
  Output,
  signal,
  WritableSignal
} from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";

import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";
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

export type AttributeMappingRow = {
  privacyideaAttr: string | null;
  userStoreAttr: string;
};

@Component({
  selector: "app-http-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatSlideToggle,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider
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

  ngOnInit(): void {
    if (this.isAdvanced) {
      this.basicSettings.set(false);
    }

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
      if (!(this.data() as any)[c]) {
        (this.data() as any)[c] = {};
      }
    });

    const existing = (this.data() as any)?.attribute_mapping as Record<string, string> | undefined;

    if (!existing || Object.keys(existing).length === 0) {
      this.syncMappingToData();
    }
  }


  protected isCustomAttr(value: string | null): boolean {
    return value === this.CUSTOM_ATTR_VALUE;
  }

  protected setCustomAttr(rowIndex: number, customValue: string): void {
    const v = (customValue ?? "").trim();
    const rows = [...this.mappingRows()];
    rows[rowIndex].privacyideaAttr = v ? v : null;
    this.mappingRows.set(rows);
    this.onMappingChanged();
  }

  protected onPrivacyIdeaAttrChanged(rowIndex: number): void {
    if (this.mappingRows()[rowIndex].privacyideaAttr === this.CUSTOM_ATTR_VALUE) return;
    this.onMappingChanged();
  }

  protected addMappingRow(): void {
    this.mappingRows.update(rows => [
      ...rows,
      { privacyideaAttr: null, userStoreAttr: "" }
    ]);
    this.syncMappingToData();
  }

  protected removeMappingRow(index: number): void {
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
