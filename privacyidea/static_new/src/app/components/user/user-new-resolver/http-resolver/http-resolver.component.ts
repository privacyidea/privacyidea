import { Component, EventEmitter, Input, OnInit, Output, signal, WritableSignal } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";

import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTableModule } from "@angular/material/table";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

import { SQLResolverData } from "../../../../services/resolver/resolver.service";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatDivider } from "@angular/material/list";

type AttributeMappingRow = {
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
  @Input() data: Partial<SQLResolverData> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();
  protected basicSettings: WritableSignal<boolean> = signal(true);
  protected mappingRows: AttributeMappingRow[] = [
    { privacyideaAttr: "userid", userStoreAttr: "userid" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenname" }
  ];

  ngOnInit(): void {
    const existing = (this.data as any)?.attribute_mapping as Record<string, string> | undefined;

    if (existing && Object.keys(existing).length > 0) {
      this.mappingRows = Object.entries(existing).map(([privacyideaAttr, userStoreAttr]) => ({
        privacyideaAttr,
        userStoreAttr
      }));
    } else {
      this.syncMappingToData();
    }
  }

  protected isCustomAttr(value: string | null): boolean {
    return value === this.CUSTOM_ATTR_VALUE;
  }

  protected setCustomAttr(rowIndex: number, customValue: string): void {
    const v = (customValue ?? "").trim();
    this.mappingRows[rowIndex].privacyideaAttr = v ? v : null;
    this.onMappingChanged();
  }

  protected onPrivacyIdeaAttrChanged(rowIndex: number): void {
    if (this.mappingRows[rowIndex].privacyideaAttr === this.CUSTOM_ATTR_VALUE) return;
    this.onMappingChanged();
  }

  protected addMappingRow(): void {
    this.mappingRows = [
      ...this.mappingRows,
      { privacyideaAttr: null, userStoreAttr: "" }
    ];
    this.syncMappingToData();
  }

  protected removeMappingRow(index: number): void {
    this.mappingRows = this.mappingRows.filter((_, i) => i !== index);
    this.syncMappingToData();
  }

  protected onMappingChanged(): void {
    this.syncMappingToData();
  }

  private syncMappingToData(): void {
    const map: Record<string, string> = {};

    for (const row of this.mappingRows) {
      const k = (row.privacyideaAttr ?? "").trim();
      const v = (row.userStoreAttr ?? "").trim();
      if (k && v) {
        map[k] = v;
      }
    }

    (this.data as any).attribute_mapping = map;
  }
}
