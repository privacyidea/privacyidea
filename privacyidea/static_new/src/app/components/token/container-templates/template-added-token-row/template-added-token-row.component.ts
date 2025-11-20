import { Component, effect, EventEmitter, input, Input, linkedSignal, Output } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ContainerTemplateToken } from "../../../../services/container/container.service";
import { MatExpansionModule } from "@angular/material/expansion";
import { FormsModule } from "@angular/forms";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";

@Component({
  selector: "app-template-added-token-row",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatExpansionModule,
    FormsModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule
  ],
  templateUrl: "./template-added-token-row.component.html",
  styleUrls: ["./template-added-token-row.component.scss"]
})
export class TemplateAddedTokenRowComponent {
  token = input.required<ContainerTemplateToken>();
  index = input.required<number>();
  isEditMode = input.required<boolean>();
  @Output() onEditToken = new EventEmitter<ContainerTemplateToken>();
  @Output() onDelete = new EventEmitter<number>();

  updateToken(patch: Partial<ContainerTemplateToken>) {
    this.onEditToken.emit({ ...this.token(), ...patch });
  }
  deleteToken() {
    this.onDelete.emit(this.index());
  }
}
