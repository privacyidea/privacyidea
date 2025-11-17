import { Component, Input, Output, EventEmitter } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { ContainerTemplateToken } from "../../../../../services/container/container.service";

@Component({
  selector: "app-template-added-token-row",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./template-added-token-row.component.html",
  styleUrls: ["./template-added-token-row.component.scss"]
})
export class TemplateAddedTokenRowComponent {
  @Input() token!: ContainerTemplateToken;
  @Output() edit = new EventEmitter<ContainerTemplateToken>();
  @Output() delete = new EventEmitter<ContainerTemplateToken>();

  editToken() {
    this.edit.emit(this.token);
  }

  deleteToken() {
    this.delete.emit(this.token);
  }
}
