import { Component, EventEmitter, inject, Input, Output, ViewEncapsulation } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatChipListbox, MatChipsModule } from "@angular/material/chips";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "../../../../services/container-template/container-template.service";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-container-template-add-token-chips",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatChipsModule, MatChipListbox, MatIcon],
  templateUrl: "./container-template-add-token-chips.component.html",
  styleUrls: ["./container-template-add-token-chips.component.scss"]
})
export class ContainerTemplateAddTokenChipsComponent {
  @Input({ required: true }) containerType: string = "";
  @Output() onAddToken = new EventEmitter<string>();

  containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);

  get tokenTypes(): string[] {
    return this.containerTemplateService.getTokenTypesForContainerType(this.containerType);
  }

  addToken(tokenType: string) {
    this.onAddToken.emit(tokenType);
  }
}
