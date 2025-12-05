export type DialogAction<R = any> = {
  type:
    | "confirm" // Confirmation/Save/Submit
    | "cancel" // Rejection/Discard/Return
    | "destruct" // Delete/Irreversible/Deactivate
    | "auxiliary"; // Help/Navigation/Secondary Actions
  label: string;
  value: R;
  closeOnAction?: boolean;
  disabled?: boolean;
};
