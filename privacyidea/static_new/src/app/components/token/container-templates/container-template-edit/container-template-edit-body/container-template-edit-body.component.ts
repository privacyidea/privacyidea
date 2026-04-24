import { Component, computed, model } from "@angular/core";
import { MatChipsModule } from "@angular/material/chips";
import { MatIcon } from "@angular/material/icon";
import { TokenEnrollmentPayload } from "src/app/mappers/token-api-payload/_token-api-payload.mapper";
import { ContainerTemplate } from "src/app/services/container/container.service";
import { TokenTypeKey } from "src/app/services/token/token.service";
import { TemplateAddedTokenRowComponent } from "../../dialogs/container-template-edit-dialog/template-added-token-row/template-added-token-row.component";

@Component({
  selector: "app-container-template-edit-body",
  standalone: true,
  imports: [TemplateAddedTokenRowComponent, MatChipsModule, MatIcon],
  templateUrl: "./container-template-edit-body.component.html",
  styleUrl: "./container-template-edit-body.component.scss"
})
export class ContainerTemplateEditBodyComponent {
  readonly template = model.required<ContainerTemplate>();
  readonly availableTokenTypes = model.required<string[]>();

  protected readonly tokens = computed(() => this.template().template_options?.tokens || []);

  protected onEditToken(patch: Partial<TokenEnrollmentPayload>, index: number) {
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

  protected onDeleteToken(index: number) {
    this.updateTokens(this.tokens().filter((_, i) => i !== index));
  }
  // --- Private Helper Methods ---
  private updateTokens(tokens: TokenEnrollmentPayload[]) {
    const editedTemplate: ContainerTemplate = {
      ...this.template(),
      template_options: {
        ...this.template().template_options,
        tokens
      }
    };
    this.template.set(editedTemplate);
  }

  protected onAddToken(tokenType: string) {
    const updatedTokens = [...this.tokens(), { type: tokenType as TokenTypeKey }];
    this.updateTokens(updatedTokens);
  }

  protected _toTitleCase(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
