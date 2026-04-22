import { Component, Input, model, output } from "@angular/core";
import { ContainerTemplateAddTokenComponent } from "../../dialogs/container-template-edit-dialog/container-template-add-token-chips/container-template-add-token.component";
import { TemplateAddedTokenRowComponent } from "../../dialogs/container-template-edit-dialog/template-added-token-row/template-added-token-row.component";
import { ContainerTemplate } from "src/app/services/container/container.service";
import { TokenTypeKey } from "src/app/services/token/token.service";
import { TokenEnrollmentPayload } from "src/app/mappers/token-api-payload/_token-api-payload.mapper";

@Component({
  selector: "app-container-template-edit-body",
  standalone: true,
  imports: [ContainerTemplateAddTokenComponent, TemplateAddedTokenRowComponent],
  templateUrl: "./container-template-edit-body.component.html",
  styleUrl: "./container-template-edit-body.component.scss"
})
export class ContainerTemplateEditBodyComponent {
  template = model.required<ContainerTemplate>();
  availableTokenTypes = model.required<string[]>();
  tokens = model.required<TokenEnrollmentPayload[]>();

  editTemplate = output<Partial<ContainerTemplate>>();

  trackByIndex(index: number) {
    return index;
  }

  onEditToken(patch: Partial<TokenEnrollmentPayload>, index: number) {
    const updatedTokens = this.tokens().map((token, i) => {
      if (i !== index) return token;
      const updatedToken = { ...token, ...patch };
      Object.keys(updatedToken).forEach((key) => {
        if (updatedToken[key] === undefined) {
          delete updatedToken[key];
        }
      });
      return updatedToken;
    });
    this.updateTokens(updatedTokens);
  }

  onDeleteToken(index: number) {
    this.updateTokens(this.tokens().filter((_, i) => i !== index));
  }
  // --- Private Helper Methods ---
  private updateTokens(tokens: TokenEnrollmentPayload[]) {
    this.editTemplate.emit({
      template_options: {
        ...this.template().template_options,
        tokens
      }
    });
  }

  onAddToken(tokenType: string) {
    const updatedTokens = [...this.tokens(), { type: tokenType as TokenTypeKey }];
    this.updateTokens(updatedTokens);
  }
}
