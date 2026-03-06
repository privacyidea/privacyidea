import { Component, inject, input } from "@angular/core";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { MatButton } from "@angular/material/button";
import { DialogServiceInterface, DialogService } from "src/app/services/dialog/dialog.service";
import { ContainerTemplateNewComponent } from "../dialogs/container-template-new/container-template-new.component";

@Component({
  selector: "app-container-templates-table-actions",
  standalone: true,
  templateUrl: "./container-templates-table-actions.component.html",
  styleUrl: "./container-templates-table-actions.component.scss",
  imports: [MatButton]
})
export class ContainerTemplatesTableActionsComponent {
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly selectedContainerTemplates = input.required<ContainerTemplate[]>();
  openNewTemplateDialog() {
    this.dialogService.openDialog({
      component: ContainerTemplateNewComponent
    });
  }
}
